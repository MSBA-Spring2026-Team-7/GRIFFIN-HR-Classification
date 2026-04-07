-- ============================================================
-- W&M HR Position Classification & Pay Matching Tool
-- Database Schema v1.0
-- 
-- Open in MySQL Workbench, then use:
--   Database > Reverse Engineer to generate visual ERD
--   or simply run the script to create the schema
-- ============================================================

CREATE DATABASE IF NOT EXISTS wm_hr_classification;
USE wm_hr_classification;

-- ============================================================
-- Table 1: CAREER_GROUPS
-- Top-level classification entity. ~56 rows.
-- One row per DHRM Career Group.
-- The concept_of_work narrative is the primary text
-- an LLM matches against when classifying positions.
-- ============================================================
CREATE TABLE career_groups (
    career_group_code   VARCHAR(5)      NOT NULL    COMMENT '4-digit DHRM code, e.g. 19030',
    career_group_name   VARCHAR(100)    NOT NULL    COMMENT 'e.g. Financial Services',
    occupational_family VARCHAR(100)    NOT NULL    COMMENT 'e.g. Administrative Services',
    occ_family_code     VARCHAR(2)      NOT NULL    COMMENT 'First 2 digits of career group code, e.g. 19',
    pay_band_min        INT             NOT NULL    COMMENT 'Lowest pay band in this group',
    pay_band_max        INT             NOT NULL    COMMENT 'Highest pay band in this group',
    concept_of_work     TEXT            NOT NULL    COMMENT 'Full narrative description of what this career group covers',
    source_url          VARCHAR(500)    NULL        COMMENT 'URL of the DHRM career group page',
    source_format       VARCHAR(10)     NULL        COMMENT 'html or pdf',
    effective_date      DATE            NULL        COMMENT 'Date career group description became effective',
    data_source         VARCHAR(50)     DEFAULT 'DHRM_PUBLIC' COMMENT 'DHRM_PUBLIC or PROPRIETARY, for tracking origin',
    last_updated        TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (career_group_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
COMMENT='DHRM Career Groups - top level of classification hierarchy. ~56 groups across 7 Occupational Families.';


-- ============================================================
-- Table 2: ROLES
-- Core classification target. ~200-250 rows.
-- Each role has compensable factor descriptions used
-- by the LLM to determine the correct level within
-- a career group. The track field distinguishes
-- practitioner vs management roles at the same pay band.
-- ============================================================
CREATE TABLE roles (
    role_code           VARCHAR(5)      NOT NULL    COMMENT '5-digit DHRM role code, e.g. 19036',
    role_name           VARCHAR(150)    NOT NULL    COMMENT 'e.g. Financial Services Manager III',
    career_group_code   VARCHAR(5)      NOT NULL    COMMENT 'FK to career_groups, 4-digit parent code',
    pay_band            INT             NOT NULL    COMMENT 'Single pay band number (1-10)',
    track               VARCHAR(20)     NOT NULL    COMMENT 'practitioner or management',
    role_summary        TEXT            NULL        COMMENT 'Introductory paragraph describing the role',
    complexity          TEXT            NULL        COMMENT 'Compensable Factor: Complexity description',
    results             TEXT            NULL        COMMENT 'Compensable Factor: Results description',
    accountability      TEXT            NULL        COMMENT 'Compensable Factor: Accountability description',
    data_source         VARCHAR(50)     DEFAULT 'DHRM_PUBLIC' COMMENT 'DHRM_PUBLIC or PROPRIETARY',
    last_updated        TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (role_code),
    CONSTRAINT fk_roles_career_group
        FOREIGN KEY (career_group_code) REFERENCES career_groups(career_group_code)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
COMMENT='DHRM Roles - classification targets within career groups. Each has 3 compensable factors (Complexity, Results, Accountability).';


-- ============================================================
-- Table 3: HISTORICAL_TITLES
-- Maps former class codes/titles to current roles.
-- Critical for identifying legacy positions that need
-- reclassification. This is where HR proprietary data
-- adds the most value - they likely have internal title
-- histories not in public DHRM data.
-- ============================================================
CREATE TABLE historical_titles (
    id                  INT             AUTO_INCREMENT,
    role_code           VARCHAR(5)      NOT NULL    COMMENT 'FK to roles - the current role this title maps to',
    former_class_code   VARCHAR(10)     NOT NULL    COMMENT 'Previous classification code, e.g. 23136',
    former_class_title  VARCHAR(200)    NOT NULL    COMMENT 'Previous title, e.g. Assistant Comptroller',
    former_grade        INT             NULL        COMMENT 'Previous pay grade number, e.g. 19',
    data_source         VARCHAR(50)     DEFAULT 'DHRM_PUBLIC' COMMENT 'DHRM_PUBLIC or PROPRIETARY',
    last_updated        TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_hist_role (role_code),
    INDEX idx_hist_class_code (former_class_code),
    INDEX idx_hist_title (former_class_title),
    CONSTRAINT fk_hist_role
        FOREIGN KEY (role_code) REFERENCES roles(role_code)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
COMMENT='Legacy class title mappings to current roles. HR can add proprietary rows using the same schema.';


-- ============================================================
-- Table 4: SOC_CODES
-- Links career groups (and optionally roles) to Bureau of
-- Labor Statistics Standard Occupational Classification codes.
-- 
-- CRITICAL DESIGN NOTE: SOC codes are a federal standard used
-- across government HR systems including Workday and Banner.
-- If HR's proprietary data is organized by SOC code, this
-- table becomes the JOIN KEY that bridges the public DHRM
-- dataset to their internal data. The role_code FK allows
-- mapping at both career group and individual role granularity.
-- ============================================================
CREATE TABLE soc_codes (
    id                  INT             AUTO_INCREMENT,
    career_group_code   VARCHAR(5)      NOT NULL    COMMENT 'FK to career_groups',
    role_code           VARCHAR(5)      NULL        COMMENT 'FK to roles - NULL if SOC maps at group level, populated if role-specific',
    soc_code            VARCHAR(10)     NOT NULL    COMMENT 'BLS SOC code, e.g. 13-2010',
    soc_title           VARCHAR(200)    NULL        COMMENT 'BLS title, e.g. Accountants and Auditors',
    mapping_level       VARCHAR(15)     NOT NULL    DEFAULT 'career_group' COMMENT 'career_group or role - indicates granularity of the mapping',
    data_source         VARCHAR(50)     DEFAULT 'DHRM_PUBLIC' COMMENT 'DHRM_PUBLIC or PROPRIETARY',
    last_updated        TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_soc_group (career_group_code),
    INDEX idx_soc_role (role_code),
    INDEX idx_soc_code (soc_code),
    CONSTRAINT fk_soc_career_group
        FOREIGN KEY (career_group_code) REFERENCES career_groups(career_group_code)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_soc_role
        FOREIGN KEY (role_code) REFERENCES roles(role_code)
        ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
COMMENT='SOC code crosswalk - bridges DHRM taxonomy to BLS national standards. Potential join key for proprietary HR data that uses SOC classification.';


-- ============================================================
-- Table 5: DHRM_PAY_BANDS
-- Virginia state salary structure.
-- Source: FY26 Salary Structure PDF, effective 6/10/2025.
-- Roughly 10 rows (Bands 1-10).
-- ============================================================
CREATE TABLE dhrm_pay_bands (
    pay_band            INT             NOT NULL    COMMENT 'Band number (1-10)',
    annual_min          DECIMAL(12,2)   NOT NULL    COMMENT 'FY26 annual minimum salary',
    annual_midpoint     DECIMAL(12,2)   NULL        COMMENT 'FY26 annual midpoint salary',
    annual_max          DECIMAL(12,2)   NOT NULL    COMMENT 'FY26 annual maximum salary',
    hourly_min          DECIMAL(8,2)    NULL        COMMENT 'Hourly equivalent minimum, if applicable',
    hourly_midpoint     DECIMAL(8,2)    NULL        COMMENT 'Hourly equivalent midpoint, if applicable',
    hourly_max          DECIMAL(8,2)    NULL        COMMENT 'Hourly equivalent maximum, if applicable',
    effective_date      DATE            NOT NULL    DEFAULT '2025-06-10' COMMENT 'Effective date of this pay structure',
    fiscal_year         VARCHAR(10)     NOT NULL    DEFAULT 'FY26' COMMENT 'Fiscal year identifier',
    last_updated        TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (pay_band)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
COMMENT='DHRM state salary structure by pay band. Updated annually with new fiscal year rates.';


-- ============================================================
-- Table 6: WM_PAY_GRADES
-- William & Mary university salary structure.
-- Source: W&M UHR website, effective 6/10/2025.
-- S01-S23 (salaried) and H01-H23 (hourly).
-- The mapped_dhrm_band field provides the crosswalk
-- between W&M grades and DHRM pay bands.
-- ============================================================
CREATE TABLE wm_pay_grades (
    pay_grade           VARCHAR(5)      NOT NULL    COMMENT 'W&M grade code, e.g. S18 or H08',
    grade_type          VARCHAR(10)     NOT NULL    COMMENT 'salaried or hourly',
    annual_min          DECIMAL(12,2)   NULL        COMMENT 'Annual minimum (salaried grades)',
    annual_midpoint     DECIMAL(12,2)   NULL        COMMENT 'Annual midpoint (salaried grades)',
    annual_max          DECIMAL(12,2)   NULL        COMMENT 'Annual maximum (salaried grades)',
    hourly_min          DECIMAL(8,2)    NULL        COMMENT 'Hourly minimum (hourly grades)',
    hourly_midpoint     DECIMAL(8,2)    NULL        COMMENT 'Hourly midpoint (hourly grades)',
    hourly_max          DECIMAL(8,2)    NULL        COMMENT 'Hourly maximum (hourly grades)',
    mapped_dhrm_band    INT             NULL        COMMENT 'FK to dhrm_pay_bands - the crosswalk link',
    effective_date      DATE            NOT NULL    DEFAULT '2025-06-10' COMMENT 'Effective date',
    last_updated        TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (pay_grade),
    INDEX idx_wm_dhrm_band (mapped_dhrm_band),
    CONSTRAINT fk_wm_dhrm_band
        FOREIGN KEY (mapped_dhrm_band) REFERENCES dhrm_pay_bands(pay_band)
        ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
COMMENT='W&M university salary structure with crosswalk to DHRM pay bands. All employees hired since 2009 use this structure.';


-- ============================================================
-- VIEWS: Useful pre-built queries for the classification tool
-- ============================================================

-- Full classification lookup: role + career group + pay info
CREATE OR REPLACE VIEW v_classification_lookup AS
SELECT
    r.role_code,
    r.role_name,
    r.track,
    r.pay_band,
    cg.career_group_code,
    cg.career_group_name,
    cg.occupational_family,
    cg.occ_family_code,
    cg.concept_of_work,
    r.role_summary,
    r.complexity,
    r.results,
    r.accountability,
    dpb.annual_min     AS dhrm_annual_min,
    dpb.annual_midpoint AS dhrm_annual_midpoint,
    dpb.annual_max     AS dhrm_annual_max,
    wm.pay_grade       AS wm_pay_grade,
    wm.annual_min      AS wm_annual_min,
    wm.annual_midpoint AS wm_annual_midpoint,
    wm.annual_max      AS wm_annual_max
FROM roles r
JOIN career_groups cg ON r.career_group_code = cg.career_group_code
LEFT JOIN dhrm_pay_bands dpb ON r.pay_band = dpb.pay_band
LEFT JOIN wm_pay_grades wm ON dpb.pay_band = wm.mapped_dhrm_band
    AND wm.grade_type = 'salaried';


-- Historical title search: find current role from a legacy title
CREATE OR REPLACE VIEW v_title_search AS
SELECT
    ht.former_class_code,
    ht.former_class_title,
    ht.former_grade,
    r.role_code,
    r.role_name,
    r.pay_band,
    cg.career_group_code,
    cg.career_group_name,
    cg.occupational_family
FROM historical_titles ht
JOIN roles r ON ht.role_code = r.role_code
JOIN career_groups cg ON r.career_group_code = cg.career_group_code;


-- Career group summary: quick overview of all groups with role counts
CREATE OR REPLACE VIEW v_career_group_summary AS
SELECT
    cg.career_group_code,
    cg.career_group_name,
    cg.occupational_family,
    cg.pay_band_min,
    cg.pay_band_max,
    COUNT(r.role_code) AS role_count,
    SUM(CASE WHEN r.track = 'practitioner' THEN 1 ELSE 0 END) AS practitioner_roles,
    SUM(CASE WHEN r.track = 'management' THEN 1 ELSE 0 END) AS management_roles,
    COUNT(ht.id) AS historical_title_count
FROM career_groups cg
LEFT JOIN roles r ON cg.career_group_code = r.career_group_code
LEFT JOIN historical_titles ht ON r.role_code = ht.role_code
GROUP BY cg.career_group_code, cg.career_group_name,
         cg.occupational_family, cg.pay_band_min, cg.pay_band_max;


-- ============================================================
-- SAMPLE DATA: W&M Pay Grades (Salaried)
-- From W&M UHR website, effective 6/10/2025
-- ============================================================
INSERT INTO wm_pay_grades (pay_grade, grade_type, annual_min, annual_midpoint, annual_max, mapped_dhrm_band, effective_date) VALUES
('S01', 'salaried', 32240.00, 36988.83, 41737.66, NULL, '2025-06-10'),
('S02', 'salaried', 32240.00, 39075.61, 45911.22, NULL, '2025-06-10'),
('S03', 'salaried', 32240.00, 41371.48, 50502.96, NULL, '2025-06-10'),
('S04', 'salaried', 32240.00, 43896.53, 55553.05, NULL, '2025-06-10'),
('S05', 'salaried', 32240.00, 45784.00, 59328.00, NULL, '2025-06-10'),
('S06', 'salaried', 32240.00, 49729.93, 67219.86, NULL, '2025-06-10'),
('S07', 'salaried', 32240.00, 53090.82, 73941.64, NULL, '2025-06-10'),
('S08', 'salaried', 35136.00, 58235.49, 81334.98, NULL, '2025-06-10'),
('S09', 'salaried', 38649.00, 64058.94, 89468.89, NULL, '2025-06-10'),
('S10', 'salaried', 42514.00, 70465.25, 98416.50, NULL, '2025-06-10'),
('S11', 'salaried', 46766.00, 77512.07, 108258.15, NULL, '2025-06-10'),
('S12', 'salaried', 51442.00, 85262.72, 119083.45, NULL, '2025-06-10'),
('S13', 'salaried', 56587.00, 93789.14, 130991.28, NULL, '2025-06-10'),
('S14', 'salaried', 62245.00, 103167.91, 144090.82, NULL, '2025-06-10'),
('S15', 'salaried', 68470.00, 113485.26, 158500.82, NULL, '2025-06-10'),
('S16', 'salaried', 75317.00, 124833.06, 174349.13, NULL, '2025-06-10'),
('S17', 'salaried', 82848.00, 137317.00, 191786.00, NULL, '2025-06-10'),
('S18', 'salaried', 91133.00, 151048.28, 210963.57, NULL, '2025-06-10'),
('S19', 'salaried', 100247.00, 166153.51, 232060.03, NULL, '2025-06-10'),
('S20', 'salaried', 110271.00, 182768.98, 255266.96, NULL, '2025-06-10'),
('S21', 'salaried', 121299.00, 201046.22, 280793.45, NULL, '2025-06-10'),
('S22', 'salaried', 133428.00, 221149.62, 308871.25, NULL, '2025-06-10'),
('S23', 'salaried', 146771.00, 238317.50, 339759.52, NULL, '2025-06-10');


-- ============================================================
-- SAMPLE DATA: W&M Pay Grades (Hourly)
-- ============================================================
INSERT INTO wm_pay_grades (pay_grade, grade_type, hourly_min, hourly_midpoint, hourly_max, mapped_dhrm_band, effective_date) VALUES
('H01', 'hourly', 15.50, 17.78, 20.06, NULL, '2025-06-10'),
('H02', 'hourly', 15.50, 18.79, 22.07, NULL, '2025-06-10'),
('H03', 'hourly', 15.50, 19.89, 24.28, NULL, '2025-06-10'),
('H04', 'hourly', 15.50, 21.10, 26.71, NULL, '2025-06-10'),
('H05', 'hourly', 15.50, 22.44, 29.38, NULL, '2025-06-10'),
('H06', 'hourly', 15.50, 23.91, 32.32, NULL, '2025-06-10'),
('H07', 'hourly', 15.50, 25.01, 35.55, NULL, '2025-06-10'),
('H08', 'hourly', 16.89, 27.99, 39.10, NULL, '2025-06-10'),
('H09', 'hourly', 18.58, 30.80, 43.01, NULL, '2025-06-10'),
('H10', 'hourly', 20.44, 33.88, 47.32, NULL, '2025-06-10'),
('H11', 'hourly', 22.48, 37.26, 52.05, NULL, '2025-06-10'),
('H12', 'hourly', 24.73, 40.99, 57.25, NULL, '2025-06-10'),
('H13', 'hourly', 27.21, 45.09, 62.97, NULL, '2025-06-10'),
('H14', 'hourly', 29.93, 49.60, 69.28, NULL, '2025-06-10'),
('H15', 'hourly', 32.92, 54.56, 76.20, NULL, '2025-06-10'),
('H16', 'hourly', 36.21, 60.02, 83.82, NULL, '2025-06-10'),
('H17', 'hourly', 39.83, 66.02, 92.21, NULL, '2025-06-10'),
('H18', 'hourly', 43.81, 72.62, 101.42, NULL, '2025-06-10'),
('H19', 'hourly', 48.20, 79.88, 111.57, NULL, '2025-06-10'),
('H20', 'hourly', 53.01, 87.87, 122.72, NULL, '2025-06-10'),
('H21', 'hourly', 58.32, 96.66, 134.99, NULL, '2025-06-10'),
('H22', 'hourly', 64.15, 106.32, 148.50, NULL, '2025-06-10'),
('H23', 'hourly', 70.56, 116.95, 163.35, NULL, '2025-06-10');


-- ============================================================
-- SAMPLE DATA: Financial Services Career Group (validated example)
-- This demonstrates the data structure with one complete
-- career group, used to validate the Assistant Controller test case.
-- ============================================================
INSERT INTO career_groups (career_group_code, career_group_name, occupational_family, occ_family_code, pay_band_min, pay_band_max, concept_of_work, source_url, source_format, effective_date) VALUES
('19030', 'Financial Services', 'Administrative Services', '19', 4, 8,
'This Career Group provides career tracks for financial specialists who perform, evaluate, or manage financial activities involving public assets and resources in accordance with applicable professional standards. Employees perform the full range of fiscal or evaluation duties associated with specialized areas such as accounting, budgeting, grants administration, auditing or taxation. Typical duties may include, but are not limited to, strategic planning; risk evaluation and mitigation; consulting; financial analysis; forecasting; accounts reconciliation; cash management; and investments. Employees duties range from entry-level specialist to executive management.',
'https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/admin/FinancialServices19030.htm',
'html', '2001-11-01');


INSERT INTO roles (role_code, role_name, career_group_code, pay_band, track, role_summary, complexity, results, accountability) VALUES
('19031', 'Financial Services Specialist I', '19030', 4, 'practitioner',
'The Financial Specialist I role provides career tracks for tax examiners, grant specialists, collectors, accountants and others performing entry-level to first-line supervisory responsibilities ensuring or evaluating compliance and accountability of financial programs and business operations/processes.',
'Performs work requiring analysis of data and application of applicable professional principles and standards. Applies knowledge of accounting functions or principles, general business practices, collection procedures, and/or applicable computer systems. Requires knowledge of state and federal laws, rules, and regulations. Demonstrated ability to research, investigate, analyze, reconcile, and evaluate data. Interacts frequently with internal and external customers using both verbal and written communication skills to discuss financial processes or issues.',
'Applies, interprets, or assesses existing policies, procedures, laws, and regulations with potentially considerable financial or operational impact on agencies, program participants, and the general public. Effective decision-making and accurate analysis of data facilitates the efficient use of time, money, and resources.',
'Functions within well-defined guidelines and procedures to resolve routine issues, and to make independent and logical decisions and/or recommendations. May provide project or team leadership or supervise staff.'),

('19032', 'Financial Services Specialist II', '19030', 5, 'practitioner',
'The Financial Services Specialist II role provides career tracks for financial analysts performing advanced-level responsibilities analyzing and evaluating data in one or more specialty areas including, but not limited to, resources management, business operations/processes, budgets, and financial systems.',
'Performs work of varied and considerable difficulty requiring advanced data collection, analysis, forecasting, and compiling and writing reports. Applies knowledge of accounting principles, auditing standards, budgeting practices, public administration, and/or legal and regulatory compliance. Interacts frequently with internal and external senior officials, professionals, and the public requiring a high level of communication skills to analyze or resolve issues. Develops, interprets, and/or evaluates compliance with policies and procedures.',
'Significant impact with the potential to gain or lose public goodwill and revenues from multiple sources. Significant impact on various statewide and/or institutional systems. May impact policy and budget decisions at agency level. Decisions made impact the effectiveness and efficiency of administrative and business processes.',
'Works independently or as a team member within existing guidelines and policies. May provide peer assistance in specialty area or serve as a leader for a team or small work unit. Serves as a resource to others in resolving more complex problems. Exercises considerable discretion and judgment in making recommendations related to the allocation of funds, payment rates, expenditures or investments.'),

('19033', 'Financial Services Specialist III', '19030', 6, 'practitioner',
'The Financial Services Specialist III role provides career track for expert financial specialists who provide professional financial, analytical, technical, and policy/program expertise relating to areas such as reimbursements, resources management, and data collection or information systems.',
'Performs work involving analyzing data and formulating projections and plans. Applies knowledge of principles and techniques of subject matter. Interacts frequently with elected officials and senior executives requiring a high level of communication skills to plan, negotiate, and coordinate financial settlements, investments, cash flow, or similar issues.',
'Substantial impacts on resources, investments, cash flow, and state budgeting. Substantial impact with the potential to gain or lose federal funds or to involve the Commonwealth in controversy and/or litigation. May have substantial impact on Commonwealth credit rating and interest rates.',
'Exhibits a high level of autonomy through independent decision making, project management, and sound judgment. Serves as an expert technical advisor. Recommends and develops regulations, policies, and procedures.'),

('19034', 'Financial Services Manager I', '19030', 5, 'management',
'The Financial Services Manager I role provides career tracks for first level managers involved in planning and managing assigned specialty areas such as grants, accounts payable, accounts receivable, taxation, budgeting, and other financial operations. Employees may be the single position through which all financial information flows.',
'Performs managerial work involving the analysis and interpretation of financial and/or operational issues. May supervise or evaluate a variety of financial or operational functions or have statewide responsibility for a specialized program. Applies knowledge of accounting principles, auditing standards, public administration, and/or regulatory compliance. Frequent interaction with internal and external customers, including management, using both verbal and written communication skills to resolve management issues.',
'Actively and accurately uses sound management techniques and financial policies in the appropriate use of the Commonwealth resources. Actions impact the potential to gain or lose Commonwealth revenues and public goodwill. May impact policy and budget decisions at agency level.',
'Manages personnel, including training, evaluating, and assigning work, where applicable. Manages staff, programs, and/or projects by determining objectives and allocating resources. May involve the supervision of subordinate technical employees as well as first-line supervisors. Ensures or evaluates compliance with applicable state and federal laws and regulations.'),

('19035', 'Financial Services Manager II', '19030', 6, 'management',
'The Financial Services Manager II role provides career tracks for senior level managers involved in planning, organizing, and administering personnel and programs relating to one or more specialized areas such as resource management, business operations, budget, and financial systems.',
'Applies knowledge of financial, accounting, and auditing functions, as well as agency, state and federal laws and regulations regarding financial operations, business processes, information systems, and reporting requirements. Contacts include the public, other state agencies, all levels of government officials, and private organizations to discuss financial issues.',
'Significant impact on the effectiveness, credibility, and financial responsibility of the agency, programs, customer service, and public relations. Decisions may result in a significant impact on the financial resources, goodwill, and appropriate use of the Commonwealth resources.',
'Demonstrates comprehensive analysis and decision-making skills to implement quality improvements and assess effectiveness of changes. Exercises significant independent judgment in decision-making, program administration, and interpretation of rules and regulations. Serves as a resource to others in solving complex and sensitive problems.'),

('19036', 'Financial Services Manager III', '19030', 7, 'management',
'The Financial Services Manager III role provides career tracks for managers serving as directors or comptrollers involved in the overall direction and leadership of specialized financial programs. May direct the overall fiscal or audit management of an agency or institution having diverse and complicated financial and regulatory requirements or may direct the statewide function of a principle financial area to ensure achievement of organizational mission and goals.',
'Applies knowledge of accounting, auditing, financial, and/or information systems. Resolves complex problems and sensitive policy issues. Effective interaction with diverse constituencies to include the public, other state agencies, General Assembly members, government officials, and private organizations to discuss programs and policies.',
'Decisions have agency-wide and statewide impact on the effectiveness and credibility of the organization. Decisions may result in a far-reaching impact on the appropriate use of the Commonwealth financial resources.',
'Broad range of independent decision making authority using sound judgment. Formulates, implements, and interprets policies and regulations. May supervise a large and diverse professional staff.'),

('19037', 'Financial Services Manager IV', '19030', 8, 'management',
'The Financial Services Manager IV role provides career tracks for executives responsible for policies, procedures, and standards that ensure the protection of the Commonwealth fiscal assets and meet program goals. Employees have statutory and regulatory (both state and federal) responsibilities to provide for the development and maintenance of financially sound, high-quality programs and services.',
'Performs work involving strategic planning and interpreting complex rules and regulations. Projects often address controversial, unprecedented, and sensitive issues. Applies knowledge of subject area with advanced education and appropriate professional certification preferred. Contacts include the public, other state agencies, all levels of government officials, and private organizations to resolve critical and sensitive issues.',
'Decisions have agency-wide and statewide impact for both the short- and long-term. Effective job performance ensures financial integrity and compliance with federal and state regulations and guidelines.',
'Effective leadership of programs that are essential to meeting agency goals, statutory mandates, and delivery of services. Interprets, administers, and enforces agency policies and procedures. Requires complex problem resolution with wide-ranging implications. Leads and directs the effective utilization of resources to accomplish organizational goals and/or legislative mandates.');


-- Historical titles for Financial Services (validated example data)
INSERT INTO historical_titles (role_code, former_class_code, former_class_title, former_grade) VALUES
('19031', '24282', 'Unemployment Tax Representative', 11),
('19031', '22071', 'Grants Specialist', 9),
('19031', '22072', 'Grants Administrator', 10),
('19031', '23011', 'Tax Collections Representative', 9),
('19031', '23414', 'Accountant', 9),
('19031', '23415', 'Accountant Senior', 11),
('19031', '23431', 'Budget Analyst', 10),
('19032', '23132', 'State Senior Accounting/Financial Analyst', 12),
('19032', '23134', 'State Lead Financial Reporting Analyst', 13),
('19032', '23135', 'State Lead Accounting Analyst', 13),
('19032', '23432', 'Budget Analyst Senior', 12),
('19033', '22201', 'Health Care Reimbursement Specialist', 15),
('19033', '23116', 'Cash Administrator', 16),
('19033', '23122', 'State Debt Management Advisor', 16),
('19034', '23401', 'Fiscal Officer', 12),
('19034', '23402', 'Fiscal Director A', 14),
('19034', '23416', 'Accounting Manager A', 12),
('19034', '23417', 'Accounting Manager B', 14),
('19034', '23433', 'Budget Manager', 14),
('19035', '23133', 'Accounts Department Assistant Fiscal Manager', 15),
('19035', '23403', 'Fiscal Director B', 16),
('19035', '23418', 'Accounting Manager C', 15),
('19035', '23434', 'Budget Director', 17),
('19036', '23106', 'Transportation Financial Planning and Debt Management Director', 18),
('19036', '23121', 'State Debt Management Director', 18),
('19036', '23131', 'Accounts Department Fiscal Manager', 18),
('19036', '23136', 'Assistant Comptroller', 19),
('19036', '23404', 'Controller', 18),
('19036', '25114', 'ABC Chief Financial Officer', 19),
('19036', '28322', 'Investment Officer', 19),
('19037', '23115', 'State Deputy Treasurer', 21),
('19037', '23123', 'Treasury Cash Management and Investments Director', 21);


-- SOC codes for Financial Services
-- Group-level mappings (from "Statistical Reporting" section)
INSERT INTO soc_codes (career_group_code, role_code, soc_code, soc_title, mapping_level) VALUES
('19030', NULL, '11-3030', 'Financial Managers', 'career_group'),
('19030', NULL, '13-2000', 'Financial Specialists', 'career_group'),
('19030', NULL, '13-2010', 'Accountants & Auditors', 'career_group'),
('19030', NULL, '13-2080', 'Tax Examiners, Collectors, Preparers & Revenue Agents', 'career_group'),
('19030', NULL, '13-2099', 'Financial Specialists, All Others', 'career_group'),
-- Role-level mappings (from individual role headers on the page)
('19030', '19031', '13-2000', 'Financial Specialists', 'role'),
('19030', '19032', '13-2000', 'Financial Specialists', 'role'),
('19030', '19033', '13-2000', 'Financial Specialists', 'role'),
('19030', '19034', '11-3030', 'Financial Managers', 'role'),
('19030', '19035', '11-3030', 'Financial Managers', 'role'),
('19030', '19036', '11-3030', 'Financial Managers', 'role'),
('19030', '19037', '11-3030', 'Financial Managers', 'role');


-- ============================================================
-- CLASSIFICATION OUTPUT TABLES
-- These tables store the results when a position description
-- is run through the classification tool. They provide the
-- audit trail for how a classification was determined,
-- including blended role handling.
-- ============================================================

-- ============================================================
-- Table 7: POSITION_DESCRIPTIONS
-- Stores the input position descriptions submitted for
-- classification. One row per submission.
-- ============================================================
CREATE TABLE position_descriptions (
    pd_id               INT             AUTO_INCREMENT,
    position_title      VARCHAR(200)    NOT NULL    COMMENT 'Current or proposed title',
    legacy_title        VARCHAR(200)    NULL        COMMENT 'Former/legacy title if known, e.g. Deputy Comptroller Assistant',
    department          VARCHAR(200)    NULL        COMMENT 'Department or unit, e.g. AVP Financial Operations',
    description_text    TEXT            NOT NULL    COMMENT 'Full position description text as submitted',
    last_salary         DECIMAL(12,2)   NULL        COMMENT 'Previous incumbent salary if known',
    last_salary_date    DATE            NULL        COMMENT 'Date of last salary for inflation adjustment',
    posted_salary_min   DECIMAL(12,2)   NULL        COMMENT 'Posted range minimum if available',
    posted_salary_max   DECIMAL(12,2)   NULL        COMMENT 'Posted range maximum if available',
    submitted_by        VARCHAR(100)    NULL        COMMENT 'HR analyst who submitted the classification request',
    submitted_date      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    status              VARCHAR(20)     DEFAULT 'pending' COMMENT 'pending, classified, reviewed, approved',
    PRIMARY KEY (pd_id),
    INDEX idx_pd_title (position_title),
    INDEX idx_pd_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
COMMENT='Input position descriptions submitted for classification. Each row triggers one classification analysis.';


-- ============================================================
-- Table 8: CLASSIFICATION_RESULTS
-- Stores the overall classification outcome for each PD.
-- Links to primary and (optionally) secondary roles.
-- Contains the blend determination and final pay recommendation.
-- This is the auditable record of the classification decision.
-- ============================================================
CREATE TABLE classification_results (
    result_id           INT             AUTO_INCREMENT,
    pd_id               INT             NOT NULL    COMMENT 'FK to position_descriptions',
    classification_type VARCHAR(10)     NOT NULL    COMMENT 'single or blended',
    blend_threshold     INT             NOT NULL    DEFAULT 30 COMMENT 'Threshold percentage applied (configurable, default 30)',

    -- Primary classification (always populated)
    primary_role_code       VARCHAR(5)  NOT NULL    COMMENT 'FK to roles - dominant role',
    primary_career_group    VARCHAR(5)  NOT NULL    COMMENT 'FK to career_groups',
    primary_duty_pct        INT         NOT NULL    COMMENT 'Percentage of duties mapped to primary (0-100)',
    primary_pay_band        INT         NOT NULL    COMMENT 'DHRM pay band for primary role',
    primary_wm_grade        VARCHAR(5)  NULL        COMMENT 'W&M pay grade for primary role',

    -- Secondary classification (populated only when blended)
    secondary_role_code     VARCHAR(5)  NULL        COMMENT 'FK to roles - secondary role, NULL if single classification',
    secondary_career_group  VARCHAR(5)  NULL        COMMENT 'FK to career_groups',
    secondary_duty_pct      INT         NULL        COMMENT 'Percentage of duties mapped to secondary',
    secondary_pay_band      INT         NULL        COMMENT 'DHRM pay band for secondary role',
    secondary_wm_grade      VARCHAR(5)  NULL        COMMENT 'W&M pay grade for secondary role',

    -- Compensation recommendation (calculated output)
    recommended_min         DECIMAL(12,2)   NULL    COMMENT 'Recommended minimum (weighted if blended)',
    recommended_midpoint    DECIMAL(12,2)   NULL    COMMENT 'Recommended midpoint (weighted if blended)',
    recommended_max         DECIMAL(12,2)   NULL    COMMENT 'Recommended maximum (weighted if blended)',
    inflation_adjusted_salary DECIMAL(12,2) NULL    COMMENT 'Previous salary adjusted to current dollars, if applicable',

    -- Explanation and audit
    explanation_narrative   TEXT            NULL     COMMENT 'Full human-readable explanation of classification and pay determination',
    confidence_notes        TEXT            NULL     COMMENT 'Any caveats, edge cases, or recommendations for HR review',
    llm_provider            VARCHAR(50)     NULL    COMMENT 'Which LLM produced this result (Claude, Copilot, Gemini, etc.)',

    -- Review workflow
    reviewed_by             VARCHAR(100)    NULL    COMMENT 'HR analyst who reviewed the result',
    reviewed_date           TIMESTAMP       NULL,
    review_decision         VARCHAR(20)     NULL    COMMENT 'accepted, modified, rejected',
    review_notes            TEXT            NULL     COMMENT 'HR notes on the classification decision',

    created_date            TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (result_id),
    INDEX idx_cr_pd (pd_id),
    INDEX idx_cr_primary_role (primary_role_code),
    INDEX idx_cr_secondary_role (secondary_role_code),
    INDEX idx_cr_type (classification_type),
    CONSTRAINT fk_cr_pd
        FOREIGN KEY (pd_id) REFERENCES position_descriptions(pd_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_cr_primary_role
        FOREIGN KEY (primary_role_code) REFERENCES roles(role_code)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_cr_primary_group
        FOREIGN KEY (primary_career_group) REFERENCES career_groups(career_group_code)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_cr_secondary_role
        FOREIGN KEY (secondary_role_code) REFERENCES roles(role_code)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_cr_secondary_group
        FOREIGN KEY (secondary_career_group) REFERENCES career_groups(career_group_code)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
COMMENT='Classification outcomes with blend determination, pay recommendation, explanation narrative, and HR review workflow.';


-- ============================================================
-- Table 9: DUTY_MAPPINGS
-- Stores the individual duty-to-role mappings that support
-- the classification result. Each major duty block from the
-- position description gets one row, showing which career
-- group and role it was mapped to and what percentage of
-- the overall position it represents.
-- This is the evidence trail for the blend calculation.
-- ============================================================
CREATE TABLE duty_mappings (
    mapping_id          INT             AUTO_INCREMENT,
    result_id           INT             NOT NULL    COMMENT 'FK to classification_results',
    duty_area           VARCHAR(200)    NOT NULL    COMMENT 'Name of the duty block, e.g. Financial Operations & Compliance',
    duty_description    TEXT            NULL        COMMENT 'Summary of duties in this block',
    duty_percentage     INT             NOT NULL    COMMENT 'Percentage of position allocated to this duty area (0-100)',
    mapped_career_group VARCHAR(5)      NOT NULL    COMMENT 'FK to career_groups - best fit for this duty block',
    mapped_role_code    VARCHAR(5)      NOT NULL    COMMENT 'FK to roles - best fit role for this duty block',
    mapping_rationale   TEXT            NULL        COMMENT 'Why this career group/role was selected for this duty block',
    PRIMARY KEY (mapping_id),
    INDEX idx_dm_result (result_id),
    INDEX idx_dm_group (mapped_career_group),
    INDEX idx_dm_role (mapped_role_code),
    CONSTRAINT fk_dm_result
        FOREIGN KEY (result_id) REFERENCES classification_results(result_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_dm_career_group
        FOREIGN KEY (mapped_career_group) REFERENCES career_groups(career_group_code)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_dm_role
        FOREIGN KEY (mapped_role_code) REFERENCES roles(role_code)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
COMMENT='Individual duty-to-role mappings supporting each classification. Evidence trail for blend calculations.';


-- ============================================================
-- VIEW: Full classification report with blend details
-- ============================================================
CREATE OR REPLACE VIEW v_classification_report AS
SELECT
    cr.result_id,
    pd.position_title,
    pd.legacy_title,
    pd.department,
    cr.classification_type,
    cr.blend_threshold,
    -- Primary
    cr.primary_role_code,
    pr.role_name AS primary_role_name,
    pcg.career_group_name AS primary_career_group_name,
    cr.primary_duty_pct,
    cr.primary_pay_band,
    cr.primary_wm_grade,
    -- Secondary (NULL if single)
    cr.secondary_role_code,
    sr.role_name AS secondary_role_name,
    scg.career_group_name AS secondary_career_group_name,
    cr.secondary_duty_pct,
    cr.secondary_pay_band,
    cr.secondary_wm_grade,
    -- Pay recommendation
    cr.recommended_min,
    cr.recommended_midpoint,
    cr.recommended_max,
    cr.inflation_adjusted_salary,
    pd.posted_salary_min,
    pd.posted_salary_max,
    -- Explanation
    cr.explanation_narrative,
    cr.confidence_notes,
    -- Review status
    cr.review_decision,
    cr.reviewed_by,
    cr.review_notes,
    cr.llm_provider,
    cr.created_date
FROM classification_results cr
JOIN position_descriptions pd ON cr.pd_id = pd.pd_id
JOIN roles pr ON cr.primary_role_code = pr.role_code
JOIN career_groups pcg ON cr.primary_career_group = pcg.career_group_code
LEFT JOIN roles sr ON cr.secondary_role_code = sr.role_code
LEFT JOIN career_groups scg ON cr.secondary_career_group = scg.career_group_code;


-- ============================================================
-- SAMPLE DATA: Assistant Controller classification result
-- Demonstrates the full output structure for a single
-- classification (below blend threshold)
-- ============================================================
INSERT INTO position_descriptions (pd_id, position_title, legacy_title, department, description_text, last_salary, last_salary_date, posted_salary_min, posted_salary_max, status) VALUES
(1, 'Assistant Controller', 'Deputy Comptroller Assistant', 'AVP Financial Operations',
'Under the supervision of the University Controller, the Assistant Controller helps supervise and manage the Controller''s Office and provides leadership across core accounting and financial operations to ensure accurate reporting, regulatory compliance, strong internal controls, and effective stewardship of University resources. The role supports monthly/quarterly and year-end close, financial analysis and reporting, general accounting operations, tax compliance, treasury/banking coordination, travel operations, and financial systems/data control across ERP platforms (Workday and Banner).',
85000.00, '2002-01-01', 130000.00, 150000.00, 'classified');

INSERT INTO classification_results (result_id, pd_id, classification_type, blend_threshold,
    primary_role_code, primary_career_group, primary_duty_pct, primary_pay_band, primary_wm_grade,
    secondary_role_code, secondary_career_group, secondary_duty_pct, secondary_pay_band, secondary_wm_grade,
    recommended_min, recommended_midpoint, recommended_max, inflation_adjusted_salary,
    explanation_narrative, confidence_notes, llm_provider, review_decision) VALUES
(1, 1, 'single', 30,
'19036', '19030', 80, 7, 'S18',
NULL, NULL, NULL, NULL, NULL,
91133.00, 151048.28, 210963.57, 150000.00,
'This position is classified as Financial Services Manager III (Role Code 19036, Pay Band 7) within the Financial Services Career Group (#19030), Occupational Family: Administrative Services. The primary duties (financial reporting, audit coordination, GAAP/GASB compliance, treasury management, and staff supervision) align directly with the Manager III compensable factors: work involving direction and leadership of specialized financial programs with diverse and complicated financial and regulatory requirements. The position''s CPA requirement and advanced GAAP knowledge further support the Manager III level over Manager II. While approximately 20% of duties relate to process improvement and systems management, which could map to General Administration (#19220), this falls below the 30% blend threshold and is treated as incidental. The recommended W&M pay grade is S18 ($91,133 to $210,964). The current posted range of $130,000 to $150,000 is consistent with positioning between the minimum and midpoint of S18. Historical note: the DHRM classification system maps the legacy title ''Assistant Comptroller'' (class code 23136) directly to this role, confirming the classification. An inflation adjustment of the previous salary of $85,000 from 2002 yields approximately $150,000 in 2026 dollars, which aligns with the posted range.',
'Process improvement duties (20%) could arguably map to General Administration #19220 or remain under Financial Services. Either way, below blend threshold. CPA requirement strongly supports Manager III over Manager II.',
'Claude', 'accepted');

INSERT INTO duty_mappings (result_id, duty_area, duty_description, duty_percentage, mapped_career_group, mapped_role_code, mapping_rationale) VALUES
(1, 'Financial Operations & Compliance', 'Monthly/quarterly close, financial reporting, reconciliations, audit support, tax compliance, treasury management, GAAP/GASB compliance', 50, '19030', '19036',
'Core financial management duties align directly with Financial Services Manager III compensable factors: direction and leadership of specialized financial programs with diverse and complicated financial and regulatory requirements.'),
(1, 'Process Improvement & Innovation', 'Streamline processes, enhance workflow, apply Workday functionality, lead cross-functional improvement projects, campus outreach and education', 20, '19030', '19036',
'While process improvement could map to General Administration #19220, these duties are performed in the context of financial operations improvement and are better characterized as part of the financial management role.'),
(1, 'Strategic Leadership & Oversight', 'Leadership support to Controller, oversight of managers/teams, policy development, cross-functional relationship building, committee participation', 15, '19030', '19036',
'Direct supervisory and strategic duties within financial operations. Aligns with Manager III accountability factor: broad range of independent decision making authority.'),
(1, 'Systems Management & Data Integrity', 'Finance information systems support, Banner/Workday security, IT liaison, year-end system processes, departmental reporting', 15, '19030', '19036',
'Financial systems management is integral to the Controller function. SOC 11-3030 (Financial Managers) encompasses technology oversight as part of financial management.');


-- ============================================================
-- VALIDATION QUERIES
-- ============================================================
-- Full classification report for Assistant Controller:
-- SELECT * FROM v_classification_report WHERE result_id = 1;
--
-- Duty mapping breakdown:
-- SELECT duty_area, duty_percentage, mapped_career_group, mapped_role_code, mapping_rationale
-- FROM duty_mappings WHERE result_id = 1 ORDER BY duty_percentage DESC;
--
-- Historical title search:
-- SELECT * FROM v_title_search WHERE former_class_title LIKE '%Comptroller%';
--
-- Full classification lookup:
-- SELECT * FROM v_classification_lookup WHERE role_code = '19036';
