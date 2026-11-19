-- =====================================================================
-- CampusFix sample data
-- Run AFTER schema.sql:
--   psql -U postgres -d campusfix -f seed.sql
--
-- Test accounts (email / password):
--   admin@campusfix.edu       / Admin@123     (admin)
--   it.staff@campusfix.edu    / Staff@123     (staff, IT team)
--   maint.staff@campusfix.edu / Staff@123     (staff, Maintenance team)
--   student1@campusfix.edu    / Student@123   (student)
--   student2@campusfix.edu    / Student@123   (student)
--   student3@campusfix.edu    / Student@123   (student)
--
-- Times are relative to NOW() so the SLA demo always works:
--   complaint 4  is past its SLA with no reminder  -> next SLA check sends a reminder
--   complaint 11 is past its SLA, reminder sent    -> next SLA check escalates it
-- =====================================================================

TRUNCATE notifications, complaint_comments, complaint_history, complaints, users RESTART IDENTITY CASCADE;

-- ---------------------------------------------------------------------
-- Users (ids 1-6). Passwords are bcrypt hashes, never plain text.
-- ---------------------------------------------------------------------
INSERT INTO users (full_name, email, password_hash, role, team) VALUES
('Anita Rao (Admin)',      'admin@campusfix.edu',       '$2b$12$CYkk7wsAHrFjwW7xK6EKVeWvShSoJ60EE9AiFMc3B5Th3oGhUERn.', 'admin',   NULL),
('Rahul Mehta (IT)',       'it.staff@campusfix.edu',    '$2b$12$S6IPs5Vmy/c/nPBwjPGLnOC8l.uFi9oauKzGj2KJjLsNiLbs1qau6', 'staff',   'IT'),
('Suresh Kumar (Maint.)',  'maint.staff@campusfix.edu', '$2b$12$S6IPs5Vmy/c/nPBwjPGLnOC8l.uFi9oauKzGj2KJjLsNiLbs1qau6', 'staff',   'Maintenance'),
('Priya Sharma',           'student1@campusfix.edu',    '$2b$12$.syRDr4GA1nIejBZLJnkWeQZmXUC16/jGpepIEuEIRPq1jiSi3JOC', 'student', NULL),
('Arjun Nair',             'student2@campusfix.edu',    '$2b$12$.syRDr4GA1nIejBZLJnkWeQZmXUC16/jGpepIEuEIRPq1jiSi3JOC', 'student', NULL),
('Meera Iyer',             'student3@campusfix.edu',    '$2b$12$.syRDr4GA1nIejBZLJnkWeQZmXUC16/jGpepIEuEIRPq1jiSi3JOC', 'student', NULL);


-- ---------------------------------------------------------------------
-- Complaints (ids 1-11)
-- SLA hours: Critical 4, High 24, Medium 48, Low 72
-- ---------------------------------------------------------------------
INSERT INTO complaints
    (title, description, location, category, priority, suggested_priority, status, assigned_team,
     student_id, is_possible_common_incident, incident_group_id,
     created_at, updated_at, sla_due_at, reminder_sent_at, escalated_at, resolved_at)
VALUES
-- 1
('Wi-Fi not working in Lab 3', 'The Wi-Fi keeps disconnecting every few minutes in Lab 3. Cannot open the course portal.',
 'Lab 3', 'Network/Wi-Fi', 'High', 'Medium', 'Open', 'IT',
 4, TRUE, NULL,
 NOW() - INTERVAL '2 hours', NOW() - INTERVAL '2 hours', NOW() - INTERVAL '2 hours' + INTERVAL '24 hours', NULL, NULL, NULL),
-- 2
('Internet very slow in Lab 3', 'Internet speed is extremely slow on all lab systems, pages take minutes to load.',
 'Lab 3', 'Network/Wi-Fi', 'High', 'High', 'In Progress', 'IT',
 5, TRUE, NULL,
 NOW() - INTERVAL '3 hours', NOW() - INTERVAL '1 hour', NOW() - INTERVAL '3 hours' + INTERVAL '24 hours', NULL, NULL, NULL),
-- 3
('Projector not turning on', 'The projector in Room 204 does not turn on, the power light stays red.',
 'Room 204', 'Projector', 'Medium', 'Medium', 'Open', 'IT',
 6, FALSE, NULL,
 NOW() - INTERVAL '5 hours', NOW() - INTERVAL '5 hours', NOW() - INTERVAL '5 hours' + INTERVAL '48 hours', NULL, NULL, NULL),
-- 4  (past SLA, no reminder yet)
('Lab computer PC-12 not booting', 'Computer PC-12 shows a blue screen and restarts. We have a practical exam tomorrow, urgent.',
 'Lab 1', 'Lab Computer', 'Critical', 'Critical', 'Open', 'IT',
 4, FALSE, NULL,
 NOW() - INTERVAL '6 hours', NOW() - INTERVAL '6 hours', NOW() - INTERVAL '6 hours' + INTERVAL '4 hours', NULL, NULL, NULL),
-- 5  (resolved, waiting for the student to confirm or reopen)
('Printer paper jam in library', 'The library printer jams on every page and shows a toner warning.',
 'Library', 'Printer', 'Low', 'Low', 'Resolved', 'IT',
 5, FALSE, NULL,
 NOW() - INTERVAL '2 days', NOW() - INTERVAL '1 day', NOW() - INTERVAL '2 days' + INTERVAL '72 hours', NULL, NULL, NOW() - INTERVAL '1 day'),
-- 6
('AC not cooling in seminar hall', 'The AC in the seminar hall is running but not cooling at all.',
 'Seminar Hall', 'Electrical', 'Medium', 'Medium', 'In Progress', 'Maintenance',
 6, FALSE, NULL,
 NOW() - INTERVAL '1 day', NOW() - INTERVAL '20 hours', NOW() - INTERVAL '1 day' + INTERVAL '48 hours', NULL, NULL, NULL),
-- 7  (closed)
('Ceiling fan making noise', 'The ceiling fan near the window makes a loud rattling noise.',
 'Room 101', 'Electrical', 'Low', 'Medium', 'Closed', 'Maintenance',
 4, FALSE, NULL,
 NOW() - INTERVAL '5 days', NOW() - INTERVAL '4 days', NOW() - INTERVAL '5 days' + INTERVAL '72 hours', NULL, NULL, NOW() - INTERVAL '4 days'),
-- 8  (already escalated)
('Lights flickering in reading room', 'All tube lights in the reading room flicker constantly, hard to study.',
 'Library Reading Room', 'Electrical', 'High', 'Medium', 'Escalated', 'Maintenance',
 5, FALSE, NULL,
 NOW() - INTERVAL '30 hours', NOW() - INTERVAL '4 hours', NOW() - INTERVAL '30 hours' + INTERVAL '24 hours', NOW() - INTERVAL '5 hours', NOW() - INTERVAL '4 hours', NULL),
-- 9  (staff asked for more info)
('Water leaking from washroom tap', 'A tap in the washroom is leaking and water is collecting on the floor.',
 'Block B Ground Floor', 'General Maintenance', 'Medium', 'Low', 'Need More Info', 'Maintenance',
 6, FALSE, NULL,
 NOW() - INTERVAL '10 hours', NOW() - INTERVAL '8 hours', NOW() - INTERVAL '10 hours' + INTERVAL '48 hours', NULL, NULL, NULL),
-- 10
('Smart board not responding', 'The smart board in Room 305 does not respond to touch.',
 'Room 305', 'Classroom Equipment', 'Low', 'Low', 'Open', 'IT',
 4, FALSE, NULL,
 NOW() - INTERVAL '1 hour', NOW() - INTERVAL '1 hour', NOW() - INTERVAL '1 hour' + INTERVAL '72 hours', NULL, NULL, NULL),
-- 11 (past SLA, reminder already sent -> will be escalated)
('Sparking from power socket', 'A power socket near bench 4 is sparking when anything is plugged in.',
 'Lab 2', 'Electrical', 'Critical', 'Critical', 'Open', 'Maintenance',
 5, FALSE, NULL,
 NOW() - INTERVAL '5 hours', NOW() - INTERVAL '5 hours', NOW() - INTERVAL '5 hours' + INTERVAL '4 hours', NOW() - INTERVAL '30 minutes', NULL, NULL);


-- ---------------------------------------------------------------------
-- Complaint history (timeline). changed_by NULL = done by the system.
-- ---------------------------------------------------------------------
INSERT INTO complaint_history (complaint_id, changed_by, action, old_value, new_value, note, created_at) VALUES
(1,  4, 'created', NULL, 'Open', 'Category: Network/Wi-Fi. Suggested priority: Medium. Assigned to IT team.', NOW() - INTERVAL '2 hours'),
(1,  2, 'priority_changed', 'Medium', 'High', 'Whole lab affected, same as complaint #2.', NOW() - INTERVAL '90 minutes'),
(2,  5, 'created', NULL, 'Open', 'Category: Network/Wi-Fi. Suggested priority: High. Assigned to IT team.', NOW() - INTERVAL '3 hours'),
(2,  2, 'status_changed', 'Open', 'In Progress', 'Checking the Lab 3 router.', NOW() - INTERVAL '1 hour'),
(3,  6, 'created', NULL, 'Open', 'Category: Projector. Suggested priority: Medium. Assigned to IT team.', NOW() - INTERVAL '5 hours'),
(4,  4, 'created', NULL, 'Open', 'Category: Lab Computer. Suggested priority: Critical. Assigned to IT team.', NOW() - INTERVAL '6 hours'),
(5,  5, 'created', NULL, 'Open', 'Category: Printer. Suggested priority: Low. Assigned to IT team.', NOW() - INTERVAL '2 days'),
(5,  2, 'status_changed', 'Open', 'In Progress', NULL, NOW() - INTERVAL '36 hours'),
(5,  2, 'status_changed', 'In Progress', 'Resolved', 'Cleared the paper jam and replaced the toner.', NOW() - INTERVAL '1 day'),
(6,  6, 'created', NULL, 'Open', 'Category: Electrical. Suggested priority: Medium. Assigned to Maintenance team.', NOW() - INTERVAL '1 day'),
(6,  3, 'status_changed', 'Open', 'In Progress', 'AC technician called.', NOW() - INTERVAL '20 hours'),
(7,  4, 'created', NULL, 'Open', 'Category: Electrical. Suggested priority: Medium. Assigned to Maintenance team.', NOW() - INTERVAL '5 days'),
(7,  3, 'priority_changed', 'Medium', 'Low', 'Noise only, fan still works.', NOW() - INTERVAL '5 days' + INTERVAL '1 hour'),
(7,  3, 'status_changed', 'Open', 'In Progress', NULL, NOW() - INTERVAL '4 days' - INTERVAL '6 hours'),
(7,  3, 'status_changed', 'In Progress', 'Resolved', 'Tightened the fan blades.', NOW() - INTERVAL '4 days'),
(7,  4, 'confirmed', 'Resolved', 'Closed', 'Student confirmed the fix.', NOW() - INTERVAL '3 days'),
(8,  5, 'created', NULL, 'Open', 'Category: Electrical. Suggested priority: Medium. Assigned to Maintenance team.', NOW() - INTERVAL '30 hours'),
(8,  3, 'priority_changed', 'Medium', 'High', 'Exams next week, students study here.', NOW() - INTERVAL '29 hours'),
(8,  NULL, 'sla_reminder', NULL, NULL, 'SLA deadline passed (High priority). Reminder sent to Maintenance team.', NOW() - INTERVAL '5 hours'),
(8,  NULL, 'escalated', 'Open', 'Escalated', 'Still unresolved after the SLA reminder. Escalated automatically.', NOW() - INTERVAL '4 hours'),
(9,  6, 'created', NULL, 'Open', 'Category: General Maintenance. Suggested priority: Low. Assigned to Maintenance team.', NOW() - INTERVAL '10 hours'),
(9,  3, 'priority_changed', 'Low', 'Medium', 'Slipping hazard.', NOW() - INTERVAL '9 hours'),
(9,  3, 'info_requested', 'Open', 'Need More Info', 'Which washroom exactly (boys/girls) and which tap number?', NOW() - INTERVAL '8 hours'),
(10, 4, 'created', NULL, 'Open', 'Category: Classroom Equipment. Suggested priority: Low. Assigned to IT team.', NOW() - INTERVAL '1 hour'),
(11, 5, 'created', NULL, 'Open', 'Category: Electrical. Suggested priority: Critical. Assigned to Maintenance team.', NOW() - INTERVAL '5 hours'),
(11, NULL, 'sla_reminder', NULL, NULL, 'SLA deadline passed (Critical priority). Reminder sent to Maintenance team.', NOW() - INTERVAL '30 minutes');


-- ---------------------------------------------------------------------
-- Comments
-- ---------------------------------------------------------------------
INSERT INTO complaint_comments (complaint_id, author_id, comment_type, message, is_internal, created_at) VALUES
(9, 3, 'info_request', 'Which washroom exactly (boys/girls) and which tap number?', FALSE, NOW() - INTERVAL '8 hours'),
(2, 2, 'staff_note',   'Router in Lab 3 rack looks overheated. Possibly the same incident as #1.', TRUE, NOW() - INTERVAL '50 minutes'),
(6, 3, 'staff_note',   'Gas refill needed, vendor visit scheduled.', TRUE, NOW() - INTERVAL '19 hours');


-- ---------------------------------------------------------------------
-- Notifications
-- ---------------------------------------------------------------------
INSERT INTO notifications (user_id, complaint_id, message, is_read, created_at) VALUES
(2, 1,  'New Medium complaint #1: Wi-Fi not working in Lab 3 (Lab 3)', FALSE, NOW() - INTERVAL '2 hours'),
(2, 4,  'New Critical complaint #4: Lab computer PC-12 not booting (Lab 1)', FALSE, NOW() - INTERVAL '6 hours'),
(3, 11, 'Reminder: complaint #11 ''Sparking from power socket'' is past its SLA deadline.', FALSE, NOW() - INTERVAL '30 minutes'),
(1, 8,  'Complaint #8 ''Lights flickering in reading room'' was escalated (SLA breached).', FALSE, NOW() - INTERVAL '4 hours'),
(5, 2,  'Your complaint #2 is now ''In Progress''.', FALSE, NOW() - INTERVAL '1 hour'),
(5, 5,  'Your complaint #5 is now ''Resolved''.', FALSE, NOW() - INTERVAL '1 day'),
(6, 9,  'Your complaint #9 is now ''Need More Info''.', FALSE, NOW() - INTERVAL '8 hours');
