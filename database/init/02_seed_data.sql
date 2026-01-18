-- StackDebt Encyclopedia - Initial Seed Data
-- Populate database with major software version release dates

-- Operating Systems
INSERT INTO version_releases (software_name, version, release_date, end_of_life_date, category, is_lts) VALUES
-- Ubuntu LTS versions
('Ubuntu', '22.04', '2022-04-21', '2027-04-21', 'operating_system', true),
('Ubuntu', '20.04', '2020-04-23', '2025-04-23', 'operating_system', true),
('Ubuntu', '18.04', '2018-04-26', '2023-04-26', 'operating_system', true),
('Ubuntu', '16.04', '2016-04-21', '2021-04-21', 'operating_system', true),

-- CentOS versions
('CentOS', '8', '2019-09-24', '2021-12-31', 'operating_system', false),
('CentOS', '7', '2014-07-07', '2024-06-30', 'operating_system', false),

-- Windows Server
('Windows Server', '2022', '2021-08-18', null, 'operating_system', true),
('Windows Server', '2019', '2018-10-02', '2029-01-09', 'operating_system', true),
('Windows Server', '2016', '2016-09-26', '2027-01-12', 'operating_system', true),

-- Programming Languages
-- Python versions
('Python', '3.12', '2023-10-02', null, 'programming_language', false),
('Python', '3.11', '2022-10-24', null, 'programming_language', false),
('Python', '3.10', '2021-10-04', null, 'programming_language', false),
('Python', '3.9', '2020-10-05', '2025-10-05', 'programming_language', false),
('Python', '3.8', '2019-10-14', '2024-10-14', 'programming_language', false),
('Python', '3.7', '2018-06-27', '2023-06-27', 'programming_language', false),
('Python', '2.7', '2010-07-03', '2020-01-01', 'programming_language', false),

-- Node.js versions
('Node.js', '20.0.0', '2023-04-18', null, 'programming_language', true),
('Node.js', '18.0.0', '2022-04-19', null, 'programming_language', true),
('Node.js', '16.0.0', '2021-04-20', '2024-04-30', 'programming_language', true),
('Node.js', '14.0.0', '2020-04-21', '2023-04-30', 'programming_language', true),
('Node.js', '12.0.0', '2019-04-23', '2022-04-30', 'programming_language', true),

-- Java versions
('Java', '21', '2023-09-19', null, 'programming_language', true),
('Java', '17', '2021-09-14', null, 'programming_language', true),
('Java', '11', '2018-09-25', null, 'programming_language', true),
('Java', '8', '2014-03-18', null, 'programming_language', true),

-- Go versions
('Go', '1.21', '2023-08-08', null, 'programming_language', false),
('Go', '1.20', '2023-02-01', null, 'programming_language', false),
('Go', '1.19', '2022-08-02', null, 'programming_language', false),
('Go', '1.18', '2022-03-15', null, 'programming_language', false),

-- Databases
-- PostgreSQL versions
('PostgreSQL', '16', '2023-09-14', null, 'database', false),
('PostgreSQL', '15', '2022-10-13', null, 'database', false),
('PostgreSQL', '14', '2021-09-30', null, 'database', false),
('PostgreSQL', '13', '2020-09-24', '2025-11-13', 'database', false),
('PostgreSQL', '12', '2019-10-03', '2024-11-14', 'database', false),
('PostgreSQL', '11', '2018-10-18', '2023-11-09', 'database', false),

-- MySQL versions
('MySQL', '8.0', '2018-04-19', null, 'database', false),
('MySQL', '5.7', '2015-10-21', '2023-10-21', 'database', false),
('MySQL', '5.6', '2013-02-05', '2021-02-05', 'database', false),

-- MongoDB versions
('MongoDB', '7.0', '2023-08-29', null, 'database', false),
('MongoDB', '6.0', '2022-07-19', null, 'database', false),
('MongoDB', '5.0', '2021-07-13', null, 'database', false),
('MongoDB', '4.4', '2020-07-30', '2024-02-29', 'database', false),

-- Redis versions
('Redis', '7.2', '2023-08-15', null, 'database', false),
('Redis', '7.0', '2022-04-27', null, 'database', false),
('Redis', '6.2', '2021-02-22', null, 'database', false),
('Redis', '6.0', '2020-04-30', null, 'database', false),

-- Web Servers
-- Apache HTTP Server
('Apache HTTP Server', '2.4.58', '2023-10-19', null, 'web_server', false),
('Apache HTTP Server', '2.4.57', '2023-04-07', null, 'web_server', false),
('Apache HTTP Server', '2.4.41', '2019-08-14', null, 'web_server', false),
('Apache HTTP Server', '2.2.34', '2017-07-11', '2017-07-11', 'web_server', false),

-- Nginx
('nginx', '1.25.3', '2023-10-24', null, 'web_server', false),
('nginx', '1.24.0', '2023-04-11', null, 'web_server', false),
('nginx', '1.22.1', '2022-10-19', null, 'web_server', false),
('nginx', '1.20.2', '2021-11-16', null, 'web_server', false),
('nginx', '1.18.0', '2020-04-21', null, 'web_server', false),

-- Frameworks
-- React versions
('React', '18.2.0', '2022-06-14', null, 'framework', false),
('React', '17.0.2', '2021-03-22', null, 'framework', false),
('React', '16.14.0', '2020-10-14', null, 'framework', false),

-- Django versions
('Django', '4.2', '2023-04-03', null, 'framework', true),
('Django', '4.1', '2022-08-03', '2023-12-01', 'framework', false),
('Django', '3.2', '2021-04-06', '2024-04-01', 'framework', true),
('Django', '2.2', '2019-04-01', '2022-04-11', 'framework', true),

-- Express.js versions
('Express', '4.18.2', '2022-10-08', null, 'framework', false),
('Express', '4.17.3', '2022-02-16', null, 'framework', false),
('Express', '4.16.4', '2018-10-10', null, 'framework', false),

-- FastAPI versions
('FastAPI', '0.104.1', '2023-10-30', null, 'framework', false),
('FastAPI', '0.100.0', '2023-06-09', null, 'framework', false),
('FastAPI', '0.95.0', '2023-03-13', null, 'framework', false);

-- Add more seed data as needed for comprehensive coverage