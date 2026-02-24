# Enhanced Google Places Import for OPERATIONS_MANAGER

## **Overview**

The OPERATIONS_MANAGER role can now seed data from Google Places API using a hierarchical selection interface: **Country → City → Area → Category**. This enhancement provides better control and targeting for data import operations.

## **New API Endpoints**

### **1. Enhanced Google Places Import**

**POST** `/api/v1/imports/google-places/enhanced/`

**Request Body:**
```json
{
  "country_id": "uuid-of-country",
  "city_id": "uuid-of-city", 
  "area_id": "uuid-of-area",
  "category_tags": ["uuid-of-category-1", "uuid-of-category-2"],
  "search_query": "restaurants food",
  "radius_m": 1500
}
```

**Response (202):**
```json
{
  "success": true,
  "data": {
    "batch_id": "uuid-of-batch",
    "status": "QUEUED",
    "country": "Pakistan",
    "city": "Islamabad",
    "area": "F-10",
    "categories": ["Restaurant", "Cafe"],
    "search_query": "restaurants food Restaurant Cafe",
    "radius_m": 1500,
    "poll_url": "/api/v1/imports/batch-uuid/"
  },
  "message": "Enhanced Google Places import queued successfully"
}
```

### **2. Geo Hierarchy Endpoints**

#### **Countries**
**GET** `/api/v1/imports/geo/countries/`
```json
{
  "success": true,
  "data": [
    {"id": "uuid", "name": "Pakistan", "code": "PK", "is_active": true},
    {"id": "uuid", "name": "United States", "code": "US", "is_active": true}
  ]
}
```

#### **Cities by Country**
**GET** `/api/v1/imports/geo/countries/{country_id}/cities/`
```json
{
  "success": true,
  "data": [
    {"id": "uuid", "name": "Islamabad", "slug": "islamabad", "is_active": true},
    {"id": "uuid", "name": "Lahore", "slug": "lahore", "is_active": true}
  ]
}
```

#### **Areas by City**
**GET** `/api/v1/imports/geo/cities/{city_id}/areas/`
```json
{
  "success": true,
  "data": [
    {"id": "uuid", "name": "F-10", "slug": "f-10", "is_active": true},
    {"id": "uuid", "name": "F-11", "slug": "f-11", "is_active": true}
  ]
}
```

#### **Area Details**
**GET** `/api/v1/imports/geo/areas/{area_id}/`
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "name": "F-10",
    "slug": "f-10",
    "city": {"id": "uuid", "name": "Islamabad", "slug": "islamabad"},
    "country": {"id": "uuid", "name": "Pakistan", "code": "PK"},
    "has_centroid": true,
    "centroid": {"lat": 33.6942, "lng": 73.0189},
    "parent_area_id": null
  }
}
```

#### **Category Tags**
**GET** `/api/v1/imports/tags/categories/`
```json
{
  "success": true,
  "data": [
    {"id": "uuid", "name": "Restaurant", "slug": "restaurant", "display_label": "Restaurant", "icon_name": "utensils"},
    {"id": "uuid", "name": "Cafe", "slug": "cafe", "display_label": "Cafe", "icon_name": "coffee"}
  ]
}
```

## **Enhanced Features**

### **1. Hierarchical Selection**
- **Country**: Select from active countries
- **City**: Filtered by selected country
- **Area**: Filtered by selected city (must have centroid coordinates)
- **Category**: Optional multi-select from active category tags

### **2. Enhanced Search Query**
- Base search query: `"restaurants food"`
- With categories: `"restaurants food Restaurant Cafe"`
- Improves Google Places API relevance

### **3. Validation & Error Handling**
- **Geo Hierarchy Validation**: Ensures city belongs to country, area belongs to city
- **Centroid Requirement**: Area must have GPS coordinates for search
- **Category Validation**: Only active CATEGORY type tags allowed
- **Permission Check**: Only authorized roles can access endpoints

### **4. Metadata Storage**
Enhanced imports store additional metadata:
```json
{
  "country_id": "uuid",
  "country_name": "Pakistan", 
  "city_id": "uuid",
  "city_name": "Islamabad",
  "area_id": "uuid", 
  "area_name": "F-10",
  "category_tags": [
    {"id": "uuid", "name": "Restaurant"},
    {"id": "uuid", "name": "Cafe"}
  ],
  "original_search_query": "restaurants food",
  "enhanced_search_query": "restaurants food Restaurant Cafe"
}
```

## **Role Permissions**

### **Allowed Roles**
- **SUPER_ADMIN**: Full access to all endpoints
- **CITY_MANAGER**: Full access to all endpoints  
- **OPERATIONS_MANAGER**: Full access to all endpoints ✨ **NEW**
- **DATA_QUALITY_ANALYST**: Read-only access to geo hierarchy endpoints

### **Permission Matrix**

| **Endpoint** | **Super Admin** | **City Manager** | **Operations Manager** | **Data Quality Analyst** |
|--------------|-----------------|------------------|------------------------|--------------------------|
| Enhanced Import | ✅ | ✅ | ✅ | ❌ |
| Countries List | ✅ | ✅ | ✅ | ✅ |
| Cities by Country | ✅ | ✅ | ✅ | ✅ |
| Areas by City | ✅ | ✅ | ✅ | ✅ |
| Area Details | ✅ | ✅ | ✅ | ✅ |
| Category Tags | ✅ | ✅ | ✅ | ✅ |

## **Usage Examples**

### **1. Basic Import**
```bash
curl -X POST "https://api.airads.com/api/v1/imports/google-places/enhanced/" \
  -H "Authorization: Bearer token" \
  -H "Content-Type: application/json" \
  -d '{
    "country_id": "country-uuid",
    "city_id": "city-uuid", 
    "area_id": "area-uuid",
    "search_query": "restaurants food",
    "radius_m": 1500
  }'
```

### **2. Category-Filtered Import**
```bash
curl -X POST "https://api.airads.com/api/v1/imports/google-places/enhanced/" \
  -H "Authorization: Bearer token" \
  -H "Content-Type: application/json" \
  -d '{
    "country_id": "country-uuid",
    "city_id": "city-uuid",
    "area_id": "area-uuid", 
    "category_tags": ["restaurant-uuid", "cafe-uuid"],
    "search_query": "food dining",
    "radius_m": 1200
  }'
```

### **3. Frontend Integration**
```javascript
// Get countries
const countries = await fetch('/api/v1/imports/geo/countries/');

// Get cities for selected country
const cities = await fetch(`/api/v1/imports/geo/countries/${countryId}/cities/`);

// Get areas for selected city
const areas = await fetch(`/api/v1/imports/geo/cities/${cityId}/areas/`);

// Get categories
const categories = await fetch('/api/v1/imports/tags/categories/');

// Create enhanced import
const import = await fetch('/api/v1/imports/google-places/enhanced/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    country_id,
    city_id,
    area_id,
    category_tags: selectedCategories,
    search_query: 'restaurants food',
    radius_m: 1500
  })
});
```

## **Benefits for OPERATIONS_MANAGER**

### **1. Better Targeting**
- **Geographic Precision**: Select specific areas instead of entire cities
- **Category Filtering**: Import only relevant business types
- **Radius Control**: Adjust search area size (100m - 5000m)

### **2. Improved Data Quality**
- **Hierarchical Validation**: Ensures geo data consistency
- **Centroid Verification**: Only areas with GPS coordinates can be selected
- **Category Enhancement**: Better search results with category keywords

### **3. Operational Efficiency**
- **Batch Tracking**: Enhanced metadata for better import monitoring
- **Error Prevention**: Comprehensive validation reduces failed imports
- **Audit Trail**: Complete record of import parameters and selections

### **4. User Experience**
- **Intuitive Interface**: Dropdown-based selection workflow
- **Real-time Validation**: Immediate feedback on selections
- **Progress Tracking**: Poll import status via provided URL

## **Error Handling**

### **Common Error Responses**

#### **Invalid Geo Hierarchy**
```json
{
  "success": false,
  "message": "Validation failed",
  "errors": {
    "city_id": ["City Lahore does not belong to country Pakistan"],
    "area_id": ["Area F-10 does not belong to city Lahore"]
  }
}
```

#### **Missing Centroid**
```json
{
  "success": false,
  "message": "Validation failed", 
  "errors": {
    "area_id": ["Area F-10 has no centroid coordinates set"]
  }
}
```

#### **Invalid Categories**
```json
{
  "success": false,
  "message": "Validation failed",
  "errors": {
    "category_tags": ["Invalid or inactive category tag IDs: ['uuid1', 'uuid2']"]
  }
}
```

## **Monitoring & Analytics**

### **Import Batch Status**
Poll the batch URL for real-time updates:
```json
{
  "success": true,
  "data": {
    "id": "batch-uuid",
    "status": "RUNNING", // QUEUED, RUNNING, DONE, FAILED
    "total_rows": 45,
    "processed_rows": 23,
    "error_count": 0,
    "created_at": "2026-02-24T16:30:00Z"
  }
}
```

### **Enhanced Analytics**
Enhanced imports provide better analytics:
- **Geographic Distribution**: Track imports by country/city/area
- **Category Performance**: Monitor success rates by business type
- **Radius Optimization**: Analyze effective search distances
- **Quality Metrics**: Compare enhanced vs. regular import quality

---

## **Implementation Summary**

✅ **OPERATIONS_MANAGER** can now seed Google Places data with hierarchical selection  
✅ **Enhanced validation** ensures data consistency and quality  
✅ **Category filtering** improves import relevance and targeting  
✅ **Comprehensive API** provides all necessary frontend endpoints  
✅ **Audit trail** maintains complete import operation records  
✅ **Error handling** provides clear feedback and validation  

This enhancement significantly improves the OPERATIONS_MANAGER's ability to perform targeted, high-quality data imports while maintaining the platform's data integrity and governance standards.
