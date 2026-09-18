CREATE TABLE service_categories (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    slug text NOT NULL UNIQUE,
    name text NOT NULL,
    description text NOT NULL DEFAULT '',
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT service_categories_slug_format CHECK (slug ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'),
    CONSTRAINT service_categories_name_length CHECK (char_length(name) BETWEEN 2 AND 80),
    CONSTRAINT service_categories_description_length CHECK (char_length(description) <= 240)
);

INSERT INTO service_categories (id, slug, name, description) VALUES
    ('10000000-0000-4000-8000-000000000001', 'beleza-estetica', 'Beleza e estética', 'Cabelo, maquiagem, manicure, sobrancelhas e estética não clínica.'),
    ('10000000-0000-4000-8000-000000000002', 'engenharia-arquitetura', 'Engenharia e arquitetura', 'Projetos, levantamentos e consultorias técnicas permitidas.'),
    ('10000000-0000-4000-8000-000000000003', 'contabilidade', 'Contabilidade', 'Serviços contábeis pontuais para pessoas e empresas.'),
    ('10000000-0000-4000-8000-000000000004', 'eventos', 'Eventos', 'Produção, recepção, cerimonial, garçons, bartenders e apoio.'),
    ('10000000-0000-4000-8000-000000000005', 'gastronomia', 'Gastronomia', 'Cozinha, confeitaria, barismo e serviços de alimentação.'),
    ('10000000-0000-4000-8000-000000000006', 'casa-manutencao', 'Casa e manutenção', 'Limpeza, montagem, reparos, jardinagem e manutenção geral.'),
    ('10000000-0000-4000-8000-000000000007', 'tecnologia', 'Tecnologia', 'Desenvolvimento, suporte técnico e projetos digitais.'),
    ('10000000-0000-4000-8000-000000000008', 'design-criacao', 'Design e criação', 'Design gráfico, ilustração, redação e produção criativa.'),
    ('10000000-0000-4000-8000-000000000009', 'foto-video', 'Foto e vídeo', 'Fotografia, filmagem, edição e produção audiovisual.'),
    ('10000000-0000-4000-8000-000000000010', 'marketing-comunicacao', 'Marketing e comunicação', 'Social media, conteúdo, divulgação e comunicação.'),
    ('10000000-0000-4000-8000-000000000011', 'aulas-treinamentos', 'Aulas e treinamentos', 'Aulas particulares, oficinas e treinamentos não clínicos.'),
    ('10000000-0000-4000-8000-000000000012', 'transporte-logistica', 'Transporte e logística', 'Fretes, entregas e apoio logístico conforme a legislação.'),
    ('10000000-0000-4000-8000-000000000013', 'administrativo', 'Apoio administrativo', 'Organização, atendimento, digitação e apoio operacional.'),
    ('10000000-0000-4000-8000-000000000014', 'musica-entretenimento', 'Música e entretenimento', 'DJ, música, recreação e apresentações para eventos.');

ALTER TABLE professional_profiles
    ADD COLUMN bio text NOT NULL DEFAULT '',
    ADD COLUMN primary_category_id uuid REFERENCES service_categories(id) ON DELETE SET NULL,
    ADD COLUMN skills text[] NOT NULL DEFAULT '{}',
    ADD COLUMN service_region text NOT NULL DEFAULT '',
    ADD COLUMN service_location geography(Point, 4326),
    ADD COLUMN service_radius_km integer NOT NULL DEFAULT 25,
    ADD COLUMN reference_price_cents bigint,
    ADD COLUMN available_now boolean NOT NULL DEFAULT false,
    ADD COLUMN availability_timezone text NOT NULL DEFAULT 'America/Sao_Paulo',
    ADD CONSTRAINT professional_profiles_bio_length CHECK (char_length(bio) <= 600),
    ADD CONSTRAINT professional_profiles_skills_count CHECK (cardinality(skills) <= 20),
    ADD CONSTRAINT professional_profiles_region_length CHECK (char_length(service_region) <= 120),
    ADD CONSTRAINT professional_profiles_radius_range CHECK (service_radius_km BETWEEN 1 AND 200),
    ADD CONSTRAINT professional_profiles_reference_price_range CHECK (reference_price_cents IS NULL OR reference_price_cents BETWEEN 0 AND 100000000),
    ADD CONSTRAINT professional_profiles_timezone_length CHECK (char_length(availability_timezone) BETWEEN 1 AND 64);

CREATE INDEX professional_profiles_location_gist
    ON professional_profiles USING gist (service_location);
CREATE INDEX professional_profiles_category_idx
    ON professional_profiles (primary_category_id)
    WHERE primary_category_id IS NOT NULL;

CREATE TABLE availabilities (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    professional_profile_id uuid NOT NULL REFERENCES professional_profiles(id) ON DELETE CASCADE,
    weekday smallint NOT NULL CHECK (weekday BETWEEN 0 AND 6),
    start_time time NOT NULL,
    end_time time NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT availabilities_time_order CHECK (start_time < end_time),
    CONSTRAINT availabilities_unique_period UNIQUE (professional_profile_id, weekday, start_time, end_time)
);
CREATE INDEX availabilities_profile_weekday_idx
    ON availabilities (professional_profile_id, weekday, start_time);

CREATE TABLE portfolio_items (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    professional_profile_id uuid NOT NULL REFERENCES professional_profiles(id) ON DELETE CASCADE,
    storage_key text NOT NULL UNIQUE,
    original_name text NOT NULL,
    media_type text NOT NULL CHECK (media_type IN ('image/jpeg', 'image/png')),
    size_bytes bigint NOT NULL CHECK (size_bytes BETWEEN 1 AND 5242880),
    sort_order smallint NOT NULL DEFAULT 0 CHECK (sort_order BETWEEN 0 AND 32767),
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT portfolio_items_storage_key_format CHECK (storage_key ~ '^[a-f0-9-]+\\.(jpg|png)$'),
    CONSTRAINT portfolio_items_original_name_length CHECK (char_length(original_name) BETWEEN 1 AND 255)
);
CREATE INDEX portfolio_items_profile_order_idx
    ON portfolio_items (professional_profile_id, sort_order, created_at);
