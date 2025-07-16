# Replit.md - Sesame Report Generator

## Overview

This is a Flask-based web application that generates XLSX reports from Sesame Time Tracking API data. The application provides a simple interface to generate employee activity reports with date filtering capabilities. It integrates with the Sesame API to fetch time tracking data and processes it into Excel reports for billing purposes.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: Basic HTML templates with Tailwind CSS framework
- **UI Components**: Single-page application with form-based interactions
- **Styling**: Tailwind CSS with Figtree typography and Tabler Icons
- **JavaScript**: Minimal client-side logic for form validation and API testing
- **Design System**: Indigo-500 as primary color, 32px button/input height, 12px border-radius
- **Responsive Design**: 120px margins (desktop), 56px (tablet), 16px (mobile)

### Backend Architecture
- **Framework**: Flask (Python web framework)
- **Structure**: Blueprint-based routing with separation of concerns
- **Services**: Modular service layer for API integration and report generation
- **Error Handling**: Centralized error handlers for 404 and 500 errors

### Key Components
1. **Main Application** (`app.py`): Flask app initialization and configuration
2. **Routes** (`routes/main.py`): HTTP request handling and form processing
3. **Services**:
   - `sesame_api.py`: Sesame API integration service
   - `report_generator.py`: XLSX report generation service
4. **Templates**: Jinja2 templates with Bootstrap styling
5. **Static Assets**: CSS customizations

## Data Flow

1. **User Input**: Date range and employee ID filtering through web form
2. **API Integration**: Sesame API requests for employee time tracking data
3. **Data Processing**: Time calculations and activity consolidation
4. **Report Generation**: Excel file creation with openpyxl
5. **File Download**: Direct file serving to user browser

## External Dependencies

### Third-Party APIs
- **Sesame Time Tracking API**: Primary data source for employee activities
  - Base URL: `https://api-eu1.sesametime.com`
  - Authentication: Bearer token
  - Rate limiting and error handling implemented

### Python Libraries
- **Flask**: Web framework
- **openpyxl**: Excel file generation
- **requests**: HTTP client for API calls
- **datetime**: Date/time processing

### Frontend Dependencies
- **Tailwind CSS**: Utility-first CSS framework
- **Figtree**: Google Fonts typography
- **Tabler Icons**: Modern icon library
- **CDN-delivered**: No local frontend build process

## Authentication & Configuration

- **Session Management**: Flask session with configurable secret key
- **API Authentication**: Bearer token stored in PostgreSQL database
- **Database Storage**: SesameToken model stores API tokens securely
- **Environment Variables**:
  - `DATABASE_URL`: PostgreSQL database connection
  - `SESSION_SECRET`: Flask session encryption key
- **Token Management**: Web interface for token configuration and testing

## Key Features

1. **Advanced Date Range Filtering**: Predefined date ranges with custom option
   - Today, Yesterday, Current/Last Week, Current/Last Month
   - Current Quarter, Current/Last Year, Custom range selection
   - Default selection: Current Month for optimal user experience
2. **Employee Filtering**: Optional employee ID specification
3. **Office/Center Filtering**: Filter employees by office/center
4. **Department Filtering**: Filter employees by department
5. **Report Type Selection**: Multiple report formats available:
   - Grupos y tipos de fichaje por empleado
   - Grupos y tipos de fichaje por tipo de fichaje
   - Grupos y tipos de fichaje por grupos
6. **Grouped Reporting**: Data organized by employee and date with totals
7. **Break Integration**: Breakfast breaks automatically included in adjacent activities
8. **Connection Testing**: API connectivity verification
9. **Error Handling**: User-friendly error messages and logging
10. **Excel Export**: Professional XLSX report generation with formatting and totals
11. **Database Token Storage**: Secure token management in PostgreSQL database
12. **Multi-Region Support**: Support for all Sesame API regions (eu1-eu5, br1-br2, mx1, demo1)
13. **Simplified Report Generation**: Optimized processing for stability and performance
14. **Report Preview**: Table format preview of report data before Excel generation

## Deployment Strategy

- **Development**: Local Flask development server
- **Production Ready**: Environment-based configuration
- **Logging**: Configurable logging levels
- **Error Handling**: Comprehensive error catching and user feedback
- **Static Files**: Flask static file serving
- **Port Configuration**: Configurable host and port settings

## Development Notes

- Spanish language interface (UI text in Spanish)
- Dark theme consistency throughout
- Responsive design with Bootstrap grid system
- Modular service architecture for easy testing and maintenance
- Comprehensive error logging for debugging

## Recent Changes (July 2025)

- **RESOLVED**: Fixed critical pagination issue - API was returning correct data (1177 records across 12 pages) but metadata field inconsistency caused incorrect logging
- Enhanced loading modal with progress bar and real-time status updates
- Improved debugging with detailed pagination logs showing page-by-page progress
- Corrected API response parsing to use "total" field instead of "totalItems" for accurate record counting
- Completed full application redesign with Tailwind CSS, Figtree typography, and Tabler Icons
- Implemented activity name resolution using workCheckTypeId with /schedule/v1/check-types endpoint lookup
- Overhauled break redistribution logic to redistribute non-work/remote activity time to adjacent work entries and eliminate pause lines from final output
- **Column Structure Simplification**: Replaced 4 columns (Tiempo Original, Tiempo Descanso, Tiempo Final, Procesado) with single "Tiempo Registrado" column for cleaner preview and Excel reports
- **Preview Optimization**: Limited preview to 10 records for faster loading, while Excel reports contain all data
- **Group Column**: Set to empty as group information is not yet available from API
- **Excel Report Consistency**: Updated both ReportGenerator and SimpleReportGenerator to use same 9-column structure as preview with complete data pagination
- **Break Time Redistribution**: Implemented elimination of pause entries with redistribution of pause time to adjacent work entries for cleaner reports
- **CRITICAL SSL ISSUE**: Persistent SSL connection timeouts during report generation causing "Internal Server Error"
- **Triple Fallback System**: Implemented three-tier report generation system:
  1. SimpleReportGenerator (full features)
  2. BasicReportGenerator (limited API calls)
  3. UltraBasicReportGenerator (minimal API calls, employee info only)
- **SSL Optimization**: Reduced API timeouts from (30,60) to (10,30) to (5,15) seconds
- **Connection Management**: Added connection pooling, retry logic, and proper session cleanup
- **Error Diagnostics**: Enhanced error reporting with specific SSL troubleshooting information
- **UI Simplification**: Removed employee selector due to SSL performance issues when loading 3000+ employees
- **Work-Breaks Elimination**: Removed all work-breaks API calls as requested, system now only processes work-entries data
- **New NoBreaksReportGenerator**: Created simplified report generator that focuses only on work-entries without break processing
- **Employee Data Elimination**: Removed all employee, office, and department endpoints - application now works exclusively with fichajes (work entries)
- **Background Report Generation**: Implemented async report generation system with real-time status updates
- **Download Link System**: Reports now generate in background with download links appearing below the button when ready
- **Consolidated Main Route**: Eliminated separate /generate-report endpoint - all functionality now handled in main route
- **Thread-Based Processing**: Background reports use threading to prevent SSL timeout blocking the UI
- **Real-Time Status Updates**: JavaScript polling system checks report status every 1-2 seconds with visual feedback
- **Date Range Calculation Fix**: Fixed timezone issues with current_month calculation using manual date formatting instead of toISOString()
- **Show All Entries**: Reverted break elimination logic - now shows ALL entries including breaks/pauses without redistribution
- **Code Cleanup**: Removed unused report generator files and simplified codebase to only use NoBreaksReportGenerator
- **API Sorting**: Added sorting parameters to work-entries endpoint to ensure consistent ordering by date and entry time
- **UI Cleanup**: Removed "Feature Highlight" section about breakfast breaks and "Report Information" section with column details