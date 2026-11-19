-- =====================================================================
-- CampusFix - Campus IT & Facility Issue Management System
-- Database schema (PostgreSQL)
--
-- Run this file once to create all tables:
--   psql -U postgres -d campusfix -f schema.sql
--
-- WARNING: it drops existing CampusFix tables first, so all data is lost.
-- =====================================================================

DROP TABLE IF EXISTS notifications CASCADE;
DROP TABLE IF EXISTS complaint_comments CASCADE;
DROP TABLE IF EXISTS complaint_history CASCADE;
DROP TABLE IF EXISTS complaints CASCADE;
DROP TABLE IF EXISTS users CASCADE;


-- ---------------------------------------------------------------------
-- users: everyone who can log in (students, staff, admins)
-- ---------------------------------------------------------------------
CREATE TABLE users (
    id              SERIAL PRIMARY KEY,
    full_name       VARCHAR(100) NOT NULL,
    email           VARCHAR(150) NOT NULL UNIQUE,
    password_hash   TEXT         NOT NULL,          -- bcrypt hash, never the real password
    role            VARCHAR(20)  NOT NULL DEFAULT 'student'
                    CHECK (role IN ('student', 'staff', 'admin')),
    team            VARCHAR(20)
                    CHECK (team IN ('IT', 'Maintenance')),   -- only used for staff
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    -- A staff member must belong to a team, otherwise no complaints reach them
    CONSTRAINT staff_must_have_team CHECK (role <> 'staff' OR team IS NOT NULL)
);


-- ---------------------------------------------------------------------
-- complaints: one row per issue reported by a student
-- ---------------------------------------------------------------------
CREATE TABLE complaints (
    id                          SERIAL PRIMARY KEY,
    title                       VARCHAR(150) NOT NULL,
    description                 TEXT         NOT NULL,
    location                    VARCHAR(100) NOT NULL,

    category                    VARCHAR(30)  NOT NULL
                                CHECK (category IN ('Network/Wi-Fi', 'Projector', 'Lab Computer',
                                                    'Printer', 'Classroom Equipment', 'Electrical',
                                                    'General Maintenance', 'Other')),

    -- priority = current priority (staff may override it)
    -- suggested_priority = what the rule engine suggested at creation time
    priority                    VARCHAR(10)  NOT NULL
                                CHECK (priority IN ('Low', 'Medium', 'High', 'Critical')),
    suggested_priority          VARCHAR(10)  NOT NULL
                                CHECK (suggested_priority IN ('Low', 'Medium', 'High', 'Critical')),

    status                      VARCHAR(20)  NOT NULL DEFAULT 'Open'
                                CHECK (status IN ('Open', 'In Progress', 'Need More Info',
                                                  'Resolved', 'Closed', 'Escalated')),

    assigned_team               VARCHAR(20)  NOT NULL
                                CHECK (assigned_team IN ('IT', 'Maintenance')),

    student_id                  INTEGER      NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Similarity detection: TRUE when other open complaints have the same category + location
    is_possible_common_incident BOOLEAN      NOT NULL DEFAULT FALSE,
    -- Set by staff after they verify the complaints really are the same incident
    incident_group_id           INTEGER      REFERENCES complaints(id) ON DELETE SET NULL,

    -- SLA (service level agreement) tracking
    sla_due_at                  TIMESTAMPTZ  NOT NULL,
    reminder_sent_at            TIMESTAMPTZ,
    escalated_at                TIMESTAMPTZ,
    resolved_at                 TIMESTAMPTZ,

    created_at                  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);


-- ---------------------------------------------------------------------
-- complaint_history: every change to a complaint (who, what, when)
-- ---------------------------------------------------------------------
CREATE TABLE complaint_history (
    id              SERIAL PRIMARY KEY,
    complaint_id    INTEGER     NOT NULL REFERENCES complaints(id) ON DELETE CASCADE,
    changed_by      INTEGER     REFERENCES users(id) ON DELETE SET NULL,  -- NULL = the system (SLA job)
    action          VARCHAR(30) NOT NULL,          -- e.g. 'created', 'status_changed', 'escalated'
    old_value       VARCHAR(50),
    new_value       VARCHAR(50),
    note            TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ---------------------------------------------------------------------
-- complaint_comments: messages between staff and students, plus internal staff notes
-- ---------------------------------------------------------------------
CREATE TABLE complaint_comments (
    id              SERIAL PRIMARY KEY,
    complaint_id    INTEGER     NOT NULL REFERENCES complaints(id) ON DELETE CASCADE,
    author_id       INTEGER     NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    comment_type    VARCHAR(20) NOT NULL
                    CHECK (comment_type IN ('info_request', 'info_reply', 'staff_note', 'reopen_reason')),
    message         TEXT        NOT NULL,
    is_internal     BOOLEAN     NOT NULL DEFAULT FALSE,   -- TRUE = hidden from students
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ---------------------------------------------------------------------
-- notifications: simple in-app notifications (no email)
-- ---------------------------------------------------------------------
CREATE TABLE notifications (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER     NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    complaint_id    INTEGER     REFERENCES complaints(id) ON DELETE CASCADE,
    message         TEXT        NOT NULL,
    is_read         BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ---------------------------------------------------------------------
-- Indexes: make the most common searches fast
-- ---------------------------------------------------------------------
CREATE INDEX idx_complaints_status        ON complaints (status);
CREATE INDEX idx_complaints_category      ON complaints (category);
CREATE INDEX idx_complaints_assigned_team ON complaints (assigned_team);
CREATE INDEX idx_complaints_student_id    ON complaints (student_id);
CREATE INDEX idx_history_complaint_id     ON complaint_history (complaint_id);
CREATE INDEX idx_comments_complaint_id    ON complaint_comments (complaint_id);
CREATE INDEX idx_notifications_user_id    ON notifications (user_id, is_read);
