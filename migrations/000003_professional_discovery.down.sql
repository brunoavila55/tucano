DROP TABLE IF EXISTS portfolio_items;
DROP TABLE IF EXISTS availabilities;

ALTER TABLE professional_profiles
    DROP CONSTRAINT IF EXISTS professional_profiles_timezone_length,
    DROP CONSTRAINT IF EXISTS professional_profiles_reference_price_range,
    DROP CONSTRAINT IF EXISTS professional_profiles_radius_range,
    DROP CONSTRAINT IF EXISTS professional_profiles_region_length,
    DROP CONSTRAINT IF EXISTS professional_profiles_skills_count,
    DROP CONSTRAINT IF EXISTS professional_profiles_bio_length,
    DROP COLUMN IF EXISTS availability_timezone,
    DROP COLUMN IF EXISTS available_now,
    DROP COLUMN IF EXISTS reference_price_cents,
    DROP COLUMN IF EXISTS service_radius_km,
    DROP COLUMN IF EXISTS service_location,
    DROP COLUMN IF EXISTS service_region,
    DROP COLUMN IF EXISTS skills,
    DROP COLUMN IF EXISTS primary_category_id,
    DROP COLUMN IF EXISTS bio;

DROP TABLE IF EXISTS service_categories;
