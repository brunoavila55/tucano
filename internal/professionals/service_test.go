package professionals

import (
	"encoding/json"
	"testing"

	"github.com/google/uuid"
	"github.com/stretchr/testify/require"
)

func TestValidateProfileInput(t *testing.T) {
	latitude := -23.5505
	longitude := -46.6333
	valid := ProfileInput{
		PrimaryCategoryID: uuid.New(), Skills: []string{"Barismo"}, ServiceRegion: "Centro, São Paulo — SP",
		Latitude: &latitude, Longitude: &longitude, ServiceRadiusKm: 25,
		AvailabilityTimezone: "America/Sao_Paulo",
		Availabilities:       []AvailabilityInput{{Weekday: 1, StartTime: "09:00", EndTime: "18:00"}},
	}
	require.NoError(t, validateProfileInput(valid))

	tests := []struct {
		name   string
		mutate func(*ProfileInput)
	}{
		{name: "coordinates must be paired", mutate: func(input *ProfileInput) { input.Longitude = nil }},
		{name: "latitude is bounded", mutate: func(input *ProfileInput) { invalid := 91.0; input.Latitude = &invalid }},
		{name: "radius is bounded", mutate: func(input *ProfileInput) { input.ServiceRadiusKm = 201 }},
		{name: "schedule must move forward", mutate: func(input *ProfileInput) { input.Availabilities[0].EndTime = "08:00" }},
		{name: "schedule cannot overlap", mutate: func(input *ProfileInput) {
			input.Availabilities = append(input.Availabilities, AvailabilityInput{Weekday: 1, StartTime: "17:00", EndTime: "19:00"})
		}},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			input := valid
			input.Availabilities = append([]AvailabilityInput(nil), valid.Availabilities...)
			test.mutate(&input)
			require.ErrorIs(t, validateProfileInput(input), ErrInvalidInput)
		})
	}
}

func TestNormalizeProfileSkills(t *testing.T) {
	input := normalizeProfileInput(ProfileInput{Skills: []string{" Barismo ", "barismo", "", "Atendimento"}})
	require.Equal(t, []string{"Barismo", "Atendimento"}, input.Skills)
}

func TestPublicModelsNeverExposeCoordinates(t *testing.T) {
	encoded, err := json.Marshal(SearchResult{ID: uuid.New(), ServiceRegion: "Centro", DistanceKm: 3.2})
	require.NoError(t, err)
	require.NotContains(t, string(encoded), "latitude")
	require.NotContains(t, string(encoded), "longitude")
	require.NotContains(t, string(encoded), "service_location")
}

func TestUploadPathAcceptsOnlyGeneratedImageKeys(t *testing.T) {
	service := &Service{uploadDir: "/tmp/uploads"}
	validKey := uuid.NewString() + ".jpg"
	path, ok := service.UploadPath(validKey)
	require.True(t, ok)
	require.Equal(t, "/tmp/uploads/"+validKey, path)

	for _, key := range []string{"../secret.jpg", uuid.NewString() + ".svg", "not-a-uuid.png"} {
		_, ok := service.UploadPath(key)
		require.False(t, ok)
	}
}
