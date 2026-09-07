-- KIARSY Cultural Affinity Engine — PostgreSQL schema
CREATE TABLE anchor_versions (
    version_id serial PRIMARY KEY,
    label      text NOT NULL UNIQUE,
    frozen_at  timestamptz NOT NULL DEFAULT now(),
    notes      text
);

CREATE TABLE dimensions (
    dimension_id      text PRIMARY KEY,
    dimension_name    text NOT NULL,
    dimension_type    text NOT NULL CHECK (dimension_type IN ('aesthetic','values')),
    low_label         text NOT NULL,
    high_label        text NOT NULL,
    low_anchor        text NOT NULL,
    high_anchor       text NOT NULL,
    anchor_version_id int  NOT NULL REFERENCES anchor_versions(version_id),
    sort_order        int  NOT NULL DEFAULT 0
);

CREATE TABLE universal_values (
    value_id   text PRIMARY KEY,
    value_name text NOT NULL UNIQUE,
    definition text,
    scope      text NOT NULL DEFAULT 'General' CHECK (scope IN ('General','Narrow'))
);

CREATE TABLE tiers (
    tier_name   text PRIMARY KEY,
    tier_weight numeric(3,2) NOT NULL CHECK (tier_weight BETWEEN 0 AND 1)
);

CREATE TABLE match_strengths (
    strength       text PRIMARY KEY,
    definition     text,
    test_we_apply  text,
    worked_example text
);

-- The crosswalk. Absence of a row = no loading (null). Never insert neutral filler.
CREATE TABLE value_dimension_signatures (
    value_id     text NOT NULL REFERENCES universal_values(value_id),
    dimension_id text NOT NULL REFERENCES dimensions(dimension_id),
    position     numeric(4,3) NOT NULL CHECK (position BETWEEN 0 AND 1),
    loading      numeric(3,2) NOT NULL CHECK (loading IN (1.0, 0.5)),
    rationale    text,
    confidence   text NOT NULL DEFAULT 'theory',
    PRIMARY KEY (value_id, dimension_id)
);

CREATE FUNCTION forbid_aesthetic_signatures() RETURNS trigger AS $$
BEGIN
    IF (SELECT dimension_type FROM dimensions WHERE dimension_id = NEW.dimension_id) = 'aesthetic' THEN
        RAISE EXCEPTION 'Aesthetic dimensions must not carry value signatures (design rule).';
    END IF;
    RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_no_aesthetic_signatures
BEFORE INSERT OR UPDATE ON value_dimension_signatures
FOR EACH ROW EXECUTE FUNCTION forbid_aesthetic_signatures();

CREATE TABLE cultures (
    culture_id   text PRIMARY KEY,
    culture_name text NOT NULL UNIQUE
);

CREATE TABLE symbols (
    symbol_id          text PRIMARY KEY,
    symbol_name        text NOT NULL,
    culture_id         text NOT NULL REFERENCES cultures(culture_id),
    documented_meaning text NOT NULL,
    sources            text,
    verification_level text NOT NULL DEFAULT 'probable'
        CHECK (verification_level IN ('verified','verified_candidate','probable_strong','probable')),
    usage_status       text NOT NULL DEFAULT 'open' CHECK (usage_status IN ('open','restricted')),
    usage_note         text
);

CREATE TABLE symbol_value_matches (
    symbol_id text NOT NULL REFERENCES symbols(symbol_id),
    value_id  text NOT NULL REFERENCES universal_values(value_id),
    strength  text NOT NULL REFERENCES match_strengths(strength),
    why       text,
    status    text NOT NULL DEFAULT 'ready' CHECK (status IN ('ready','flagged_for_review')),
    PRIMARY KEY (symbol_id, value_id)
);

CREATE TABLE companies (
    company_id        text PRIMARY KEY,
    company_name      text NOT NULL,
    industry          text,
    country_region    text,
    affiliate_structure text,
    websites          text,
    company_summary   text,
    date_profiled     date,
    profiled_by       text
);

CREATE TABLE company_values (
    company_id       text NOT NULL REFERENCES companies(company_id),
    value_id         text NOT NULL REFERENCES universal_values(value_id),
    tier             text NOT NULL REFERENCES tiers(tier_name),
    evidence_summary text,
    which_affiliate  text,
    sources          text,
    confidence       text,
    PRIMARY KEY (company_id, value_id)
);

CREATE TABLE scoring_runs (
    run_id            serial PRIMARY KEY,
    model_name        text NOT NULL,
    embed_model       text,
    anchor_version_id int REFERENCES anchor_versions(version_id),
    relevance_floor   numeric(4,3),
    margin_floor      numeric(4,3),
    created_at        timestamptz NOT NULL DEFAULT now()
);

-- Sentence-level evidence trail from the two-stage scorer
CREATE TABLE scored_units (
    unit_id       bigserial PRIMARY KEY,
    run_id        int  NOT NULL REFERENCES scoring_runs(run_id),
    entity_type   text NOT NULL CHECK (entity_type IN ('company','symbol')),
    company_id    text REFERENCES companies(company_id),
    symbol_id     text REFERENCES symbols(symbol_id),
    dimension_id  text NOT NULL REFERENCES dimensions(dimension_id),
    unit_text     text NOT NULL,
    relevance_sim numeric(5,3),
    margin        numeric(5,3),
    CHECK ((company_id IS NULL) <> (symbol_id IS NULL))
);

-- Aggregated NLI results. No row = no evidence = dimension excluded.
CREATE TABLE symbol_dimension_scores (
    symbol_id    text NOT NULL REFERENCES symbols(symbol_id),
    dimension_id text NOT NULL REFERENCES dimensions(dimension_id),
    run_id       int  NOT NULL REFERENCES scoring_runs(run_id),
    position     numeric(4,3) NOT NULL CHECK (position BETWEEN 0 AND 1),
    n_evidence   int  NOT NULL CHECK (n_evidence >= 1),
    confidence   numeric(4,3),
    PRIMARY KEY (symbol_id, dimension_id, run_id)
);

CREATE TABLE company_dimension_scores (
    company_id     text NOT NULL REFERENCES companies(company_id),
    dimension_id   text NOT NULL REFERENCES dimensions(dimension_id),
    run_id         int  NOT NULL REFERENCES scoring_runs(run_id),
    nli_position   numeric(4,3) CHECK (nli_position BETWEEN 0 AND 1),
    nli_confidence numeric(4,3) CHECK (nli_confidence BETWEEN 0 AND 1),
    off_topic_flag boolean NOT NULL DEFAULT false,
    prior_position numeric(4,3) CHECK (prior_position BETWEEN 0 AND 1),
    final_position numeric(4,3) CHECK (final_position BETWEEN 0 AND 1),
    n_evidence     int,
    PRIMARY KEY (company_id, dimension_id, run_id)
);

CREATE TABLE company_symbol_affinity (
    company_id        text NOT NULL REFERENCES companies(company_id),
    symbol_id         text NOT NULL REFERENCES symbols(symbol_id),
    run_id            int  NOT NULL REFERENCES scoring_runs(run_id),
    similarity        numeric(6,4) NOT NULL CHECK (similarity BETWEEN -1 AND 1),
    shared_dimensions int  NOT NULL CHECK (shared_dimensions >= 3),
    rank_in_culture   int,
    computed_at       timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (company_id, symbol_id, run_id)
);

CREATE INDEX idx_affinity_rank ON company_symbol_affinity (company_id, similarity DESC);

-- The Value Prior, computed exactly as defined:
-- prior = SUM(tier_w * loading * position) / SUM(tier_w * loading)
CREATE VIEW company_value_priors AS
SELECT cv.company_id,
       vds.dimension_id,
       SUM(t.tier_weight * vds.loading * vds.position) /
       SUM(t.tier_weight * vds.loading) AS prior_position,
       SUM(t.tier_weight * vds.loading) AS prior_strength
FROM company_values cv
JOIN tiers t ON t.tier_name = cv.tier
JOIN value_dimension_signatures vds ON vds.value_id = cv.value_id
GROUP BY cv.company_id, vds.dimension_id;

CREATE VIEW v_crosswalk_full AS
SELECT v.value_id, v.value_name, d.dimension_name, d.dimension_type,
       s.position, s.loading, s.rationale
FROM value_dimension_signatures s
JOIN universal_values v ON v.value_id = s.value_id
JOIN dimensions d ON d.dimension_id = s.dimension_id;
