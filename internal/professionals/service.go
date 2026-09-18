package professionals

import (
	"context"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"

	"github.com/brunoavila55/tucano/internal/platform/audit"
	db "github.com/brunoavila55/tucano/internal/platform/database/sqlc"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgtype"
	"github.com/jackc/pgx/v5/pgxpool"
)

const (
	maxPortfolioItems = 12
	maxUploadBytes    = 5 << 20
)

var (
	ErrInvalidInput      = errors.New("invalid professional profile input")
	ErrCategoryNotFound  = errors.New("service category not found")
	ErrLocationRequired  = errors.New("service location is required")
	ErrPortfolioFull     = errors.New("portfolio item limit reached")
	ErrPortfolioNotFound = errors.New("portfolio item not found")
	ErrUnsupportedMedia  = errors.New("unsupported portfolio media")
)

type Service struct {
	pool      *pgxpool.Pool
	queries   *db.Queries
	uploadDir string
	logger    *slog.Logger
}

type AuditContext struct {
	IPAddress string
	UserAgent string
}

type Category struct {
	ID          uuid.UUID `json:"id"`
	Slug        string    `json:"slug"`
	Name        string    `json:"name"`
	Description string    `json:"description"`
}

type AvailabilityInput struct {
	Weekday   int16  `json:"weekday"`
	StartTime string `json:"start_time"`
	EndTime   string `json:"end_time"`
}

type ProfileInput struct {
	Bio                  string              `json:"bio"`
	PrimaryCategoryID    uuid.UUID           `json:"primary_category_id"`
	Skills               []string            `json:"skills"`
	ServiceRegion        string              `json:"service_region"`
	Latitude             *float64            `json:"latitude"`
	Longitude            *float64            `json:"longitude"`
	ServiceRadiusKm      int32               `json:"service_radius_km"`
	ReferencePriceCents  *int64              `json:"reference_price_cents"`
	AvailableNow         bool                `json:"available_now"`
	AvailabilityTimezone string              `json:"availability_timezone"`
	Availabilities       []AvailabilityInput `json:"availabilities"`
}

type Availability struct {
	ID        uuid.UUID `json:"id"`
	Weekday   int16     `json:"weekday"`
	StartTime string    `json:"start_time"`
	EndTime   string    `json:"end_time"`
}

type PortfolioItem struct {
	ID           uuid.UUID `json:"id"`
	URL          string    `json:"url"`
	OriginalName string    `json:"original_name"`
	MediaType    string    `json:"media_type"`
	SizeBytes    int64     `json:"size_bytes"`
	SortOrder    int16     `json:"sort_order"`
}

type Profile struct {
	ID                   uuid.UUID       `json:"id"`
	Bio                  string          `json:"bio"`
	PrimaryCategory      *Category       `json:"primary_category"`
	Skills               []string        `json:"skills"`
	ServiceRegion        string          `json:"service_region"`
	LocationConfigured   bool            `json:"location_configured"`
	ServiceRadiusKm      int32           `json:"service_radius_km"`
	ReferencePriceCents  *int64          `json:"reference_price_cents"`
	AvailableNow         bool            `json:"available_now"`
	AvailabilityTimezone string          `json:"availability_timezone"`
	Availabilities       []Availability  `json:"availabilities"`
	Portfolio            []PortfolioItem `json:"portfolio"`
}

type SearchInput struct {
	CategoryID       uuid.UUID
	Latitude         float64
	Longitude        float64
	RadiusKm         int32
	AvailableNowOnly bool
	Page             int32
	PageSize         int32
}

type SearchResult struct {
	ID                  uuid.UUID `json:"id"`
	DisplayName         string    `json:"display_name"`
	Bio                 string    `json:"bio"`
	Category            Category  `json:"category"`
	Skills              []string  `json:"skills"`
	ServiceRegion       string    `json:"service_region"`
	ServiceRadiusKm     int32     `json:"service_radius_km"`
	ReferencePriceCents *int64    `json:"reference_price_cents"`
	AvailableNow        bool      `json:"available_now"`
	DistanceKm          float64   `json:"distance_km"`
	CoverURL            string    `json:"cover_url,omitempty"`
}

type SearchPage struct {
	Items      []SearchResult `json:"items"`
	Page       int32          `json:"page"`
	PageSize   int32          `json:"page_size"`
	Total      int64          `json:"total"`
	TotalPages int64          `json:"total_pages"`
}

func NewService(pool *pgxpool.Pool, uploadDir string, logger *slog.Logger) (*Service, error) {
	if err := os.MkdirAll(uploadDir, 0o750); err != nil {
		return nil, fmt.Errorf("create upload directory: %w", err)
	}
	return &Service{pool: pool, queries: db.New(pool), uploadDir: uploadDir, logger: logger}, nil
}

func (s *Service) Categories(ctx context.Context) ([]Category, error) {
	rows, err := s.queries.ListActiveCategories(ctx)
	if err != nil {
		return nil, fmt.Errorf("list service categories: %w", err)
	}
	result := make([]Category, 0, len(rows))
	for _, row := range rows {
		result = append(result, Category{ID: row.ID, Slug: row.Slug, Name: row.Name, Description: row.Description})
	}
	return result, nil
}

func (s *Service) GetProfile(ctx context.Context, userID uuid.UUID) (Profile, error) {
	return s.getProfile(ctx, s.queries, userID)
}

func (s *Service) UpdateProfile(ctx context.Context, userID uuid.UUID, input ProfileInput, auditContext AuditContext) (Profile, error) {
	input = normalizeProfileInput(input)
	if err := validateProfileInput(input); err != nil {
		return Profile{}, err
	}

	tx, err := s.pool.Begin(ctx)
	if err != nil {
		return Profile{}, fmt.Errorf("begin professional profile update: %w", err)
	}
	defer func() { _ = tx.Rollback(ctx) }()
	queries := s.queries.WithTx(tx)

	current, err := queries.GetProfessionalProfileView(ctx, userID)
	if err != nil {
		return Profile{}, fmt.Errorf("load professional profile: %w", err)
	}
	if !current.LocationConfigured && (input.Latitude == nil || input.Longitude == nil) {
		return Profile{}, ErrLocationRequired
	}
	if _, err := queries.GetActiveCategory(ctx, input.PrimaryCategoryID); err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return Profile{}, ErrCategoryNotFound
		}
		return Profile{}, fmt.Errorf("validate service category: %w", err)
	}
	if err := queries.UpdateProfessionalProfile(ctx, db.UpdateProfessionalProfileParams{
		Bio: input.Bio, PrimaryCategoryID: &input.PrimaryCategoryID, Skills: input.Skills,
		ServiceRegion: input.ServiceRegion, Latitude: input.Latitude, Longitude: input.Longitude,
		ServiceRadiusKm: input.ServiceRadiusKm, ReferencePriceCents: input.ReferencePriceCents,
		AvailableNow: input.AvailableNow, AvailabilityTimezone: input.AvailabilityTimezone, UserID: userID,
	}); err != nil {
		return Profile{}, fmt.Errorf("update professional profile: %w", err)
	}
	if err := queries.DeleteProfessionalAvailabilities(ctx, userID); err != nil {
		return Profile{}, fmt.Errorf("replace professional availability: %w", err)
	}
	for _, period := range input.Availabilities {
		start, _ := parseClock(period.StartTime)
		end, _ := parseClock(period.EndTime)
		if _, err := queries.CreateProfessionalAvailability(ctx, db.CreateProfessionalAvailabilityParams{
			Weekday: period.Weekday, StartTime: start, EndTime: end, UserID: userID,
		}); err != nil {
			return Profile{}, fmt.Errorf("create professional availability: %w", err)
		}
	}
	if _, err := audit.NewRecorder(queries).Record(ctx, audit.Event{
		ActorID: &userID, Action: "professional.profile_updated", Resource: "professional_profile", ResourceID: &current.ID,
		Metadata:  map[string]any{"category_id": input.PrimaryCategoryID, "service_radius_km": input.ServiceRadiusKm, "available_now": input.AvailableNow},
		IPAddress: auditContext.IPAddress, UserAgent: auditContext.UserAgent,
	}); err != nil {
		return Profile{}, fmt.Errorf("audit professional profile update: %w", err)
	}
	if err := tx.Commit(ctx); err != nil {
		return Profile{}, fmt.Errorf("commit professional profile update: %w", err)
	}
	return s.GetProfile(ctx, userID)
}

func (s *Service) AddPortfolioItem(ctx context.Context, userID uuid.UUID, originalName, mediaType string, size int64, source io.Reader, auditContext AuditContext) (PortfolioItem, error) {
	if size < 1 || size > maxUploadBytes {
		return PortfolioItem{}, ErrInvalidInput
	}
	extension := ""
	switch mediaType {
	case "image/jpeg":
		extension = ".jpg"
	case "image/png":
		extension = ".png"
	default:
		return PortfolioItem{}, ErrUnsupportedMedia
	}
	originalName = filepath.Base(strings.TrimSpace(originalName))
	if originalName == "." || len(originalName) == 0 || len(originalName) > 255 {
		return PortfolioItem{}, ErrInvalidInput
	}

	tx, err := s.pool.Begin(ctx)
	if err != nil {
		return PortfolioItem{}, fmt.Errorf("begin portfolio upload: %w", err)
	}
	defer func() { _ = tx.Rollback(ctx) }()
	queries := s.queries.WithTx(tx)
	profileID, err := queries.LockProfessionalProfile(ctx, userID)
	if err != nil {
		return PortfolioItem{}, fmt.Errorf("lock professional profile: %w", err)
	}
	count, err := queries.CountProfessionalPortfolioItems(ctx, userID)
	if err != nil {
		return PortfolioItem{}, fmt.Errorf("count portfolio items: %w", err)
	}
	if count >= maxPortfolioItems {
		return PortfolioItem{}, ErrPortfolioFull
	}

	storageKey := uuid.NewString() + extension
	path := filepath.Join(s.uploadDir, storageKey)
	// #nosec G304 -- uploadDir is operator configuration and storageKey is a generated UUID plus a fixed extension.
	file, err := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0o600)
	if err != nil {
		return PortfolioItem{}, fmt.Errorf("create portfolio file: %w", err)
	}
	written, copyErr := io.Copy(file, io.LimitReader(source, maxUploadBytes+1))
	closeErr := file.Close()
	if copyErr != nil || closeErr != nil || written != size || written > maxUploadBytes {
		_ = os.Remove(path)
		return PortfolioItem{}, ErrInvalidInput
	}

	row, err := queries.CreateProfessionalPortfolioItem(ctx, db.CreateProfessionalPortfolioItemParams{
		StorageKey: storageKey, OriginalName: originalName, MediaType: mediaType, SizeBytes: written,
		// #nosec G115 -- count is locked and bounded by maxPortfolioItems above.
		SortOrder: int16(count), UserID: userID,
	})
	if err != nil {
		_ = os.Remove(path)
		return PortfolioItem{}, fmt.Errorf("store portfolio item: %w", err)
	}
	if _, err := audit.NewRecorder(queries).Record(ctx, audit.Event{
		ActorID: &userID, Action: "professional.portfolio_item_added", Resource: "professional_profile", ResourceID: &profileID,
		Metadata:  map[string]any{"item_id": row.ID, "media_type": mediaType, "size_bytes": written},
		IPAddress: auditContext.IPAddress, UserAgent: auditContext.UserAgent,
	}); err != nil {
		_ = os.Remove(path)
		return PortfolioItem{}, fmt.Errorf("audit portfolio upload: %w", err)
	}
	if err := tx.Commit(ctx); err != nil {
		_ = os.Remove(path)
		return PortfolioItem{}, fmt.Errorf("commit portfolio upload: %w", err)
	}
	return portfolioItem(row.ID, row.StorageKey, row.OriginalName, row.MediaType, row.SizeBytes, row.SortOrder), nil
}

func (s *Service) DeletePortfolioItem(ctx context.Context, userID, itemID uuid.UUID, auditContext AuditContext) error {
	tx, err := s.pool.Begin(ctx)
	if err != nil {
		return fmt.Errorf("begin portfolio deletion: %w", err)
	}
	defer func() { _ = tx.Rollback(ctx) }()
	queries := s.queries.WithTx(tx)
	storageKey, err := queries.DeleteProfessionalPortfolioItem(ctx, db.DeleteProfessionalPortfolioItemParams{ItemID: itemID, UserID: userID})
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return ErrPortfolioNotFound
		}
		return fmt.Errorf("delete portfolio item: %w", err)
	}
	if _, err := audit.NewRecorder(queries).Record(ctx, audit.Event{
		ActorID: &userID, Action: "professional.portfolio_item_deleted", Resource: "portfolio_item", ResourceID: &itemID,
		Metadata: map[string]any{}, IPAddress: auditContext.IPAddress, UserAgent: auditContext.UserAgent,
	}); err != nil {
		return fmt.Errorf("audit portfolio deletion: %w", err)
	}
	if err := tx.Commit(ctx); err != nil {
		return fmt.Errorf("commit portfolio deletion: %w", err)
	}
	if err := os.Remove(filepath.Join(s.uploadDir, storageKey)); err != nil && !errors.Is(err, os.ErrNotExist) {
		s.logger.Warn("portfolio file cleanup failed", "item_id", itemID, "error", err)
	}
	return nil
}

func (s *Service) Search(ctx context.Context, input SearchInput) (SearchPage, error) {
	if err := validateSearchInput(input); err != nil {
		return SearchPage{}, err
	}
	if _, err := s.queries.GetActiveCategory(ctx, input.CategoryID); err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return SearchPage{}, ErrCategoryNotFound
		}
		return SearchPage{}, fmt.Errorf("validate search category: %w", err)
	}
	queryParams := db.SearchProfessionalsParams{
		Longitude: input.Longitude, Latitude: input.Latitude, CategoryID: &input.CategoryID,
		AvailableNowOnly: input.AvailableNowOnly, RadiusKm: input.RadiusKm,
		PageOffset: (input.Page - 1) * input.PageSize, PageSize: input.PageSize,
	}
	total, err := s.queries.CountSearchProfessionals(ctx, db.CountSearchProfessionalsParams{
		Longitude: input.Longitude, Latitude: input.Latitude, CategoryID: &input.CategoryID,
		AvailableNowOnly: input.AvailableNowOnly, RadiusKm: input.RadiusKm,
	})
	if err != nil {
		return SearchPage{}, fmt.Errorf("count matching professionals: %w", err)
	}
	rows, err := s.queries.SearchProfessionals(ctx, queryParams)
	if err != nil {
		return SearchPage{}, fmt.Errorf("search professionals: %w", err)
	}
	items := make([]SearchResult, 0, len(rows))
	for _, row := range rows {
		coverURL := ""
		if row.CoverStorageKey != "" {
			coverURL = "/api/uploads/" + row.CoverStorageKey
		}
		items = append(items, SearchResult{
			ID: row.ID, DisplayName: row.DisplayName, Bio: row.Bio,
			Category: Category{ID: row.CategoryID, Slug: row.CategorySlug, Name: row.CategoryName},
			Skills:   row.Skills, ServiceRegion: row.ServiceRegion, ServiceRadiusKm: row.ServiceRadiusKm,
			ReferencePriceCents: row.ReferencePriceCents, AvailableNow: row.AvailableNow,
			DistanceKm: row.DistanceKm, CoverURL: coverURL,
		})
	}
	var totalPages int64
	if total > 0 {
		totalPages = (total + int64(input.PageSize) - 1) / int64(input.PageSize)
	}
	return SearchPage{Items: items, Page: input.Page, PageSize: input.PageSize, Total: total, TotalPages: totalPages}, nil
}

func (s *Service) UploadPath(storageKey string) (string, bool) {
	if len(storageKey) != 40 || strings.ContainsAny(storageKey, "/\\") {
		return "", false
	}
	extension := filepath.Ext(storageKey)
	if extension != ".jpg" && extension != ".png" {
		return "", false
	}
	if _, err := uuid.Parse(strings.TrimSuffix(storageKey, extension)); err != nil {
		return "", false
	}
	return filepath.Join(s.uploadDir, storageKey), true
}

func (s *Service) getProfile(ctx context.Context, queries *db.Queries, userID uuid.UUID) (Profile, error) {
	row, err := queries.GetProfessionalProfileView(ctx, userID)
	if err != nil {
		return Profile{}, fmt.Errorf("load professional profile: %w", err)
	}
	periodRows, err := queries.ListProfessionalAvailabilities(ctx, userID)
	if err != nil {
		return Profile{}, fmt.Errorf("load professional availability: %w", err)
	}
	portfolioRows, err := queries.ListProfessionalPortfolioItems(ctx, userID)
	if err != nil {
		return Profile{}, fmt.Errorf("load professional portfolio: %w", err)
	}
	profile := Profile{
		ID: row.ID, Bio: row.Bio, Skills: nonNilStrings(row.Skills), ServiceRegion: row.ServiceRegion,
		LocationConfigured: row.LocationConfigured, ServiceRadiusKm: row.ServiceRadiusKm,
		ReferencePriceCents: row.ReferencePriceCents, AvailableNow: row.AvailableNow,
		AvailabilityTimezone: row.AvailabilityTimezone,
		Availabilities:       make([]Availability, 0, len(periodRows)), Portfolio: make([]PortfolioItem, 0, len(portfolioRows)),
	}
	if row.PrimaryCategoryID != nil && row.CategorySlug != nil && row.CategoryName != nil {
		profile.PrimaryCategory = &Category{ID: *row.PrimaryCategoryID, Slug: *row.CategorySlug, Name: *row.CategoryName}
	}
	for _, period := range periodRows {
		profile.Availabilities = append(profile.Availabilities, Availability{
			ID: period.ID, Weekday: period.Weekday, StartTime: formatClock(period.StartTime), EndTime: formatClock(period.EndTime),
		})
	}
	for _, item := range portfolioRows {
		profile.Portfolio = append(profile.Portfolio, portfolioItem(item.ID, item.StorageKey, item.OriginalName, item.MediaType, item.SizeBytes, item.SortOrder))
	}
	return profile, nil
}

func normalizeProfileInput(input ProfileInput) ProfileInput {
	input.Bio = strings.TrimSpace(input.Bio)
	input.ServiceRegion = strings.TrimSpace(input.ServiceRegion)
	input.AvailabilityTimezone = strings.TrimSpace(input.AvailabilityTimezone)
	seen := make(map[string]struct{}, len(input.Skills))
	normalizedSkills := make([]string, 0, len(input.Skills))
	for _, skill := range input.Skills {
		skill = strings.TrimSpace(skill)
		key := strings.ToLower(skill)
		if skill == "" {
			continue
		}
		if _, exists := seen[key]; exists {
			continue
		}
		seen[key] = struct{}{}
		normalizedSkills = append(normalizedSkills, skill)
	}
	input.Skills = normalizedSkills
	return input
}

func validateProfileInput(input ProfileInput) error {
	if len(input.Bio) > 600 || input.PrimaryCategoryID == uuid.Nil || len(input.Skills) > 20 || len(input.ServiceRegion) < 2 || len(input.ServiceRegion) > 120 {
		return ErrInvalidInput
	}
	for _, skill := range input.Skills {
		if len(skill) > 50 {
			return ErrInvalidInput
		}
	}
	if input.ServiceRadiusKm < 1 || input.ServiceRadiusKm > 200 || (input.ReferencePriceCents != nil && (*input.ReferencePriceCents < 0 || *input.ReferencePriceCents > 100000000)) {
		return ErrInvalidInput
	}
	if (input.Latitude == nil) != (input.Longitude == nil) {
		return ErrInvalidInput
	}
	if input.Latitude != nil && (*input.Latitude < -90 || *input.Latitude > 90 || *input.Longitude < -180 || *input.Longitude > 180) {
		return ErrInvalidInput
	}
	if input.AvailabilityTimezone == "" {
		return ErrInvalidInput
	}
	if _, err := time.LoadLocation(input.AvailabilityTimezone); err != nil {
		return ErrInvalidInput
	}
	if len(input.Availabilities) > 21 {
		return ErrInvalidInput
	}
	periods := append([]AvailabilityInput(nil), input.Availabilities...)
	sort.Slice(periods, func(i, j int) bool {
		if periods[i].Weekday == periods[j].Weekday {
			return periods[i].StartTime < periods[j].StartTime
		}
		return periods[i].Weekday < periods[j].Weekday
	})
	for index, period := range periods {
		start, startErr := parseClock(period.StartTime)
		end, endErr := parseClock(period.EndTime)
		if period.Weekday < 0 || period.Weekday > 6 || startErr != nil || endErr != nil || start.Microseconds >= end.Microseconds {
			return ErrInvalidInput
		}
		if index > 0 && periods[index-1].Weekday == period.Weekday {
			previousEnd, _ := parseClock(periods[index-1].EndTime)
			if previousEnd.Microseconds > start.Microseconds {
				return ErrInvalidInput
			}
		}
	}
	return nil
}

func validateSearchInput(input SearchInput) error {
	if input.CategoryID == uuid.Nil || input.Latitude < -90 || input.Latitude > 90 || input.Longitude < -180 || input.Longitude > 180 {
		return ErrInvalidInput
	}
	if input.RadiusKm < 1 || input.RadiusKm > 200 || input.Page < 1 || input.Page > 100000 || input.PageSize < 1 || input.PageSize > 50 {
		return ErrInvalidInput
	}
	return nil
}

func parseClock(value string) (pgtype.Time, error) {
	parsed, err := time.Parse("15:04", value)
	if err != nil {
		return pgtype.Time{}, err
	}
	microseconds := int64(parsed.Hour())*60*60*1_000_000 + int64(parsed.Minute())*60*1_000_000
	return pgtype.Time{Microseconds: microseconds, Valid: true}, nil
}

func formatClock(value pgtype.Time) string {
	totalMinutes := value.Microseconds / 1_000_000 / 60
	return fmt.Sprintf("%02d:%02d", totalMinutes/60, totalMinutes%60)
}

func portfolioItem(id uuid.UUID, storageKey, originalName, mediaType string, sizeBytes int64, sortOrder int16) PortfolioItem {
	return PortfolioItem{ID: id, URL: "/api/uploads/" + storageKey, OriginalName: originalName, MediaType: mediaType, SizeBytes: sizeBytes, SortOrder: sortOrder}
}

func nonNilStrings(values []string) []string {
	if values == nil {
		return []string{}
	}
	return values
}
