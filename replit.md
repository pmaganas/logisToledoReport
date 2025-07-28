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
   - Grupos y tipos de fichaje por empleado (implemented)
   - Grupos y tipos de fichaje por tipo de fichaje (implemented)
   - Grupos y tipos de fichaje por grupos (implemented)
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
- **Increased Pagination Limit**: Changed API query limit from 100 to 300 records per page to reduce total API calls and improve performance
- **Infinite Progress Bar**: Implemented simple infinite progress bar animation during report generation for better user experience
- **SSL Connection Handling**: Improved database connection management during long-running report generation to prevent SSL timeout errors
- **Downloads Management Screen**: Added comprehensive downloads page where users can view all generated reports, re-download files, and delete old reports with confirmation modal
- **Enhanced Navigation**: Added responsive navigation bar with mobile menu support for easy access to main features
- **Report Limit Management**: Implemented automatic cleanup system maintaining maximum 10 reports, oldest files deleted automatically when limit exceeded
- **Preview Functionality Removal**: Eliminated Vista Previa del Informe button and all related functionality including confirmation modal, preview table, and /preview-data endpoint - streamlined interface for direct report generation only
- **Pause Time Redistribution**: Simplified pause elimination logic - when a pause is found, the previous work entry is extended to end at the pause end time, effectively absorbing the pause duration. Next work entries remain unchanged
- **Chronological Sorting**: Implemented robust chronological sorting of work entries by entry start time (workEntryIn.date) per employee per date to ensure proper temporal ordering
- **Employee-Date Grouping**: Maintained grouping by employee and date for proper daily totals while ensuring chronological ordering within each group
- **Night Shift Sorting**: Fixed chronological ordering for night shifts by adjusting entries between 00:00-06:00 to sort after previous night's entries (22:00, 23:00, 00:00, 01:00, 02:00 sequence)
- **Null Safety**: Added comprehensive null checks for entry times to handle edge cases where work entries may not have end times (e.g., currently active sessions)
- **UI Cleanup**: Removed unnecessary flash message notification when starting background report generation - the status section already provides visual feedback
- **Connection Management Separation**: Moved all token configuration to dedicated "Conexión" section with its own page and navigation menu item
- **Simplified Connection Status**: Main page now shows simple connection indicator (connected/disconnected) with company name, full configuration moved to separate page
- **Fixed Token Status Check**: Fixed JavaScript error and API response format for proper token status detection after configuration
- **Visual Status Indicator**: Added colored circle (green/red/yellow) at the beginning of connection status for immediate visual feedback
- **Activity Name Resolution**: Implemented real activity name display in reports using workEntryType and workBreakId lookup
- **Check Types Database Cache**: Added CheckType model and CheckTypesService for caching activity types from /schedule/v1/check-types endpoint
- **Automatic Check Types Sync**: Added automatic synchronization of check types when token is configured or connection is tested
- **Activity Name Logic**: If workEntryType='work' and workBreakId=null, display "Registro normal"; if workBreakId has value, lookup name from cached check types
- **Circular Import Fix**: Resolved circular import issues by moving check types service imports inside functions to avoid module loading conflicts
- **Manual Check Types Refresh**: Added /refresh-check-types endpoint for manual synchronization of activity types when needed
- **Database Persistence**: Check types are now permanently stored in PostgreSQL database, eliminating API calls during report generation
- **Activity Names Working**: System now displays real activity names like "BAÑO", "AUDITORIA", "ABASTECER" instead of generic "work" labels
- **Production Logs Cleanup**: Removed all debugging logs (DEBUG, INFO) from services to reduce log noise in production, keeping only ERROR and WARNING logs for essential monitoring
- **urllib3 Debug Logs Suppression**: Configured logging to suppress urllib3 debug logs that show HTTP request details, keeping only WARNING and ERROR logs for clean production output
- **Security Authentication System**: Implemented secure login/logout system using environment variables ADMIN_USERNAME and ADMIN_PASSWORD with session management
- **Protected Routes**: All application routes now require authentication with @requires_auth decorator, unauthorized users redirected to login page
- **Authentication UI**: Added professional login page with Tailwind CSS styling and proper error handling for invalid credentials
- **Logout Functionality**: Added logout links in navigation and proper session cleanup with success messaging
- **Restored Office and Department Filters**: Re-enabled center and department selection dropdowns with API endpoints /get-offices and /get-departments
- **Dynamic Dropdown Loading**: Implemented JavaScript functions to populate office and department selectors from Sesame API data
- **Enhanced User Interface**: Restored filtering capabilities that were previously disabled due to SSL performance concerns
- **Connection Status Indicator**: Added visual status dot in connection tab (green=connected, red=error, orange=loading) with proper state management during token configuration and testing
- **Navigation Status Indicator**: Added connection status dot in main navigation tab visible from all pages (green=connected, red=error) with automatic updates every 30 seconds
- **Footer Layout Fix**: Implemented sticky footer using flexbox layout (html and body h-full, main flex-grow, footer mt-auto) to ensure footer always appears at bottom of screen
- **Complete Report Types Implementation**: Added missing report generation methods for "by activity type" and "by groups" to complement existing "by employee" functionality, enabling all three report formats with proper grouping and totals calculation
- **Footer Content Spacing**: Added bottom margin (mb-40) to main content to prevent overlap with sticky footer and ensure proper content visibility
- **Navigation Loading Screen**: Implemented loading modal with progress bar for tab transitions, providing visual feedback during navigation between pages with realistic progress animation
- **CSV Export Support**: Added CSV export functionality alongside existing XLSX export with dedicated green-colored button and proper mimetype handling
- **Dual Format Architecture**: Modified report generator to support both XLSX and CSV formats through format parameter with UTF-8 BOM encoding for Excel compatibility
- **Enhanced UI Buttons**: Replaced single report button with two side-by-side buttons (XLSX in indigo, CSV in green) with proper form parameter handling
- **Fixed Status Indicators**: Resolved JavaScript errors with report generation buttons and implemented comprehensive status monitoring system with visual progress indicators
- **Full Height Layout**: Modified downloads page to occupy complete viewport height with 10px footer margin, featuring fixed summary bar and scrollable table with sticky headers
- **Responsive Summary Bar**: Extracted summary statistics to full-width fixed top bar that remains visible during scroll, providing constant access to key metrics
- **Connection Close Functionality**: Implemented complete "Cerrar Conexión" feature with database cleanup, removing all tokens and check types with proper UI feedback
- **Real-Time Navigation Status**: Fixed navigation connection indicators to update immediately during all connection state changes (loading, connected, disconnected) for accurate visual feedback
- **5-Minute Progress Bar**: Replaced infinite progress animation with realistic 5-minute progress bar during report generation, including estimated time display and page refresh warnings for better user experience
- **Fixed Infinite Loop Bug**: Corrected critical bug in background report generation where report_data was reset to None before completion check, causing reports to remain in 'processing' state indefinitely
- **Enhanced Report Generation Logging**: Added comprehensive logging throughout report generation process with INFO level logging to track thread execution, API calls, and report processing status