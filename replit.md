# Replit.md - Sesame Report Generator

## Overview
This project is a Flask-based web application designed to generate XLSX and CSV reports from Sesame Time Tracking API data. Its primary purpose is to provide an easy-to-use interface for businesses to create detailed employee activity reports, filtered by various criteria like date ranges, employees, offices, departments, and report types. These reports are crucial for billing and time management. The application aims for robust performance, user-friendly design, and secure handling of API credentials, supporting multiple Sesame API regions.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### UI/UX Decisions
- **Framework**: Basic HTML templates with Tailwind CSS framework.
- **Styling**: Tailwind CSS with Figtree typography and Tabler Icons, utilizing Indigo-500 as the primary color.
- **Design Elements**: 32px button/input height, 12px border-radius, and responsive margins (120px desktop, 56px tablet, 16px mobile).
- **Language**: Spanish language interface.
- **Theme**: Consistent dark theme.
- **Interactions**: Single-page application with form-based interactions and minimal client-side JavaScript for validation and API testing.
- **Report Preview**: A streamlined interface focusing on direct report generation, eliminating the previous preview functionality.
- **Download Management**: A dedicated downloads page with a modern, card-based layout for viewing, re-downloading, and deleting reports, featuring a fixed summary bar and scrollable table with sticky headers.
- **Navigation**: Responsive navigation bar with mobile menu support and real-time connection status indicators.

### Technical Implementations
- **Backend Framework**: Flask (Python web framework).
- **Structure**: Blueprint-based routing, modular service layer for API integration and report generation.
- **Services**: `sesame_api.py` for API interaction and `report_generator.py` for XLSX/CSV report creation.
- **Report Generation**: Supports XLSX and CSV formats, with background generation using threading to prevent UI blocking and real-time status updates via JavaScript polling.
- **Data Processing**: Includes advanced date range filtering, employee/office/department filtering, grouped reporting by employee/date, chronological sorting including night shifts, and handling of work entry types.
- **Pause Handling**: Pause entries are effectively eliminated by extending previous work entries to absorb the pause duration.
- **Authentication**: Secure login/logout system using environment variables for credentials, protecting all application routes.
- **Token Management**: API bearer tokens are securely stored in a PostgreSQL database with a web interface for configuration and testing.
- **Check Type Management**: Activity types from the Sesame API are cached in the database for persistence and efficient lookup, with automatic synchronization.
- **Error Handling**: Centralized error handlers, user-friendly messages, and comprehensive logging.
- **Deployment**: Production-ready with environment-based configuration, designed for robust error handling and static file serving.

### Feature Specifications
- **Report Types**: Generation of reports by employee, activity type, and groups.
- **Filtering**: Advanced date range filtering (predefined and custom), optional employee ID, office, and department specification.
- **Output**: Professional XLSX and CSV report generation with formatting, totals, and UTF-8 BOM encoding for Excel compatibility.
- **API Optimization**: Increased API query limit for time entries to 500 records per page to reduce calls and improve performance.
- **Connection Management**: Improved SSL connection handling, retry logic, connection pooling, and proper session cleanup to mitigate timeout issues.
- **Report Progress**: Dynamic progress bar and detailed logging during report generation, displaying API pagination status and record counts.
- **Security**: Authentication system with username/password, protected routes, and token encryption.
- **Report Management**: Automatic cleanup of old reports, maintaining a maximum of 10 reports.
- **Cancellation**: Ability to cancel ongoing report generation.

## External Dependencies

### Third-Party APIs
- **Sesame Time Tracking API**: Primary data source for employee activities (`https://api-eu1.sesametime.com`). Used for fetching time tracking data, check types, offices, and departments.

### Python Libraries
- **Flask**: Web framework.
- **openpyxl**: Excel file generation.
- **requests**: HTTP client for API calls.
- **datetime**: Date/time processing.
- **psycopg2** (implied by PostgreSQL usage): PostgreSQL database adapter.

### Frontend Dependencies
- **Tailwind CSS**: Utility-first CSS framework.
- **Figtree**: Google Fonts typography.
- **Tabler Icons**: Modern icon library.
- **CDN-delivered**: Frontend assets are delivered via CDN, no local build process.