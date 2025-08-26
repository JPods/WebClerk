CREATE TABLE IF NOT EXISTS "contacts" (
    "id" BIGSERIAL PRIMARY KEY,
    "uuid" VARCHAR(36) NOT NULL UNIQUE,
    "email" VARCHAR(254) NOT NULL UNIQUE,
    "opt_out" JSONB NOT NULL DEFAULT '{}',
    "password" VARCHAR(128) NOT NULL,
    "role" TEXT[] NOT NULL DEFAULT '{}',
    "is_superuser" BOOLEAN NOT NULL DEFAULT FALSE, 
    "is_email_verified" BOOLEAN NOT NULL DEFAULT FALSE,
    "is_active" BOOLEAN NOT NULL DEFAULT TRUE,
    "is_staff" BOOLEAN NOT NULL DEFAULT FALSE,
    "attention" VARCHAR(255),
    "comment_alert" VARCHAR(255),
    "company" VARCHAR(255),
    "name_first" VARCHAR(50) NOT NULL,
    "name_last" VARCHAR(50) NOT NULL,
    "name_middle" VARCHAR(50),
    "prefix" VARCHAR(50),
    "suffix" VARCHAR(50),
    "salutation" VARCHAR(50),
    "publish" INTEGER,
    "rank" VARCHAR(50),
    "date_joined" TIMESTAMP WITH TIME ZONE NOT NULL,
    "comment" TEXT,
    "verification_code" VARCHAR(100),
    "verification_code_expiry" TIMESTAMP WITH TIME ZONE,
    "refs" JSONB NOT NULL DEFAULT '{}',
    "prefs" JSONB NOT NULL DEFAULT '{}',
    "metadata" JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS "actions" (
    "id" BIGSERIAL PRIMARY KEY,
    "uuid" UUID UNIQUE NOT NULL,
    "action" VARCHAR(255),
    "action_by" VARCHAR(255),
    "priority" VARCHAR(255),
    "difficulty" VARCHAR(255),    
    "hours" DOUBLE PRECISION,
    "percent" INTEGER,
    "status" VARCHAR(255),
    "quality" VARCHAR(255),
    "description" VARCHAR(255),
    "dt_action" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "dt_completed" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "dt_due" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "dt_updated" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "comment" TEXT,
    "refs" JSONB NOT NULL DEFAULT '{}',
    "prefs" JSONB NOT NULL DEFAULT '{}',
    "metadata" JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS "templates" (
    "id" BIGSERIAL PRIMARY KEY,
    "uuid" UUID UNIQUE NOT NULL,
    "name" VARCHAR(255),
    "purpose" VARCHAR(255),
    "table_name" VARCHAR(255),
    "comment" TEXT,
    "refs" JSONB NOT NULL DEFAULT '{}',
    "prefs" JSONB NOT NULL DEFAULT '{}',
    "metadata" JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS "settings" (
    "id" BIGSERIAL PRIMARY KEY,
    "uuid" UUID UNIQUE NOT NULL,
    "is_active" BOOLEAN DEFAULT FALSE,
    "name" VARCHAR(255),
    "purpose" VARCHAR(255),
    "role" VARCHAR(255),
    "table_name" VARCHAR(255),
    "comment" TEXT,
    "refs" JSONB NOT NULL DEFAULT '{}',
    "prefs" JSONB NOT NULL DEFAULT '{}',
    "metadata" JSONB NOT NULL DEFAULT '{}'
);
