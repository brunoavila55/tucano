package audit

import (
	"context"
	"encoding/json"
	"fmt"

	db "github.com/brunoavila55/tucano/internal/platform/database/sqlc"
	"github.com/google/uuid"
)

type Recorder struct{ queries *db.Queries }

type Event struct {
	ActorID    *uuid.UUID
	Action     string
	Resource   string
	ResourceID *uuid.UUID
	Metadata   map[string]any
	IPAddress  string
	UserAgent  string
}

func NewRecorder(queries *db.Queries) *Recorder { return &Recorder{queries: queries} }

func (r *Recorder) Record(ctx context.Context, event Event) (db.AuditEvent, error) {
	metadata, err := json.Marshal(event.Metadata)
	if err != nil {
		return db.AuditEvent{}, fmt.Errorf("encode audit metadata: %w", err)
	}
	return r.queries.CreateAuditEvent(ctx, db.CreateAuditEventParams{
		ActorID: event.ActorID, Action: event.Action, Resource: event.Resource,
		ResourceID: event.ResourceID, Metadata: metadata, IpAddress: event.IPAddress, UserAgent: event.UserAgent,
	})
}
