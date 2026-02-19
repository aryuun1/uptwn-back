
## Flow Diagrams

### 🗂️ Entity Relationship Diagram (ERD)

```mermaid
erDiagram
    users ||--o{ bookings : "makes"
    users ||--o{ booking_holds : "holds (restaurants)"
    users ||--o{ reviews : "writes"
    users ||--o{ notifications : "receives"
    users ||--o{ titles : "creates (admin)"
    users ||--o{ seat_availability : "locks"

    titles ||--o{ listings : "available at"
    titles ||--o{ title_images : "has"
    titles ||--o{ reviews : "reviewed in"

    venues ||--o{ listings : "hosts"
    venues ||--o{ halls : "has"

    halls ||--o{ time_slots : "screens"
    halls ||--o{ seats : "contains"

    listings ||--o{ time_slots : "offers"
    listings ||--o{ bookings : "booked via"

    time_slots ||--o{ bookings : "selected for"
    time_slots ||--o{ seat_availability : "tracks"

    seats ||--o{ seat_availability : "status per slot"
    seats ||--o{ booking_seats : "reserved in"

    bookings ||--o{ booking_seats : "has seats"

    time_slots ||--o{ booking_holds : "holds capacity"
    users ||--o{ booking_holds : "holds"

    users {
        uuid id PK
        varchar email UK
        varchar password_hash
        varchar full_name
        varchar role
        boolean is_active
        timestamp created_at
    }

    venues {
        uuid id PK
        varchar name
        varchar type
        varchar city
        text address
        int capacity
    }

    halls {
        uuid id PK
        uuid venue_id FK
        varchar name
        varchar screen_type
        int capacity
        boolean is_active
    }

    titles {
        uuid id PK
        category_type category
        varchar title
        varchar slug UK
        int duration_minutes
        decimal rating
        int rating_count
        jsonb metadata
        boolean is_featured
        uuid created_by FK
    }

    listings {
        uuid id PK
        uuid title_id FK
        uuid venue_id FK
        varchar city
        decimal price
        timestamp start_datetime
        int total_capacity
        varchar status
        uuid created_by FK
    }

    time_slots {
        uuid id PK
        uuid listing_id FK
        uuid hall_id FK
        date slot_date
        time start_time
        int capacity
        int booked_count
    }

    seats {
        uuid id PK
        uuid hall_id FK
        varchar row_label
        int seat_number
        varchar category
        decimal price
        boolean is_aisle
        boolean is_accessible
    }

    seat_availability {
        uuid id PK
        uuid time_slot_id FK
        uuid seat_id FK
        varchar status
        uuid locked_by FK
        timestamp locked_until
    }

    bookings {
        uuid id PK
        uuid user_id FK
        uuid listing_id FK
        uuid time_slot_id FK
        varchar booking_number UK
        int quantity
        decimal total_amount
        varchar status
    }

    booking_seats {
        uuid id PK
        uuid booking_id FK
        uuid seat_id FK
        uuid time_slot_id FK
    }

    title_images {
        uuid id PK
        uuid title_id FK
        text image_url
        int display_order
    }

    reviews {
        uuid id PK
        uuid user_id FK
        uuid title_id FK
        int rating
        text comment
    }

    booking_holds {
        uuid id PK
        uuid user_id FK
        uuid time_slot_id FK
        int quantity
        timestamp expires_at
        timestamp created_at
    }

    notifications {
        uuid id PK
        uuid user_id FK
        varchar type
        boolean is_read
    }
```

---

### 👤 Regular User Flow

```mermaid
flowchart TD
    START(("🌐 User Opens App"))
    START --> HOME["🏠 Home Page<br/><small>/</small>"]

    HOME -- "GET /titles?is_featured=true" --> FEATURED["Featured Carousel<br/>+ Category Sections"]
    FEATURED --> BROWSE_OR_CLICK{{"User Action?"}}
    BROWSE_OR_CLICK -- "Clicks category tab" --> BROWSE["📋 Browse Page<br/><small>/browse?category=movies&city=delhi</small>"]
    BROWSE_OR_CLICK -- "Clicks title card" --> DETAIL

    BROWSE -- "GET /titles?category=...&city=...&sort_by=...&page=1" --> RESULTS["Filter / Sort / Search<br/>Paginated Grid"]
    RESULTS -- "Clicks title card" --> DETAIL

    DETAIL["📄 Title Detail<br/><small>/titles/{slug}</small>"]
    DETAIL -- "GET /titles/{slug}" --> TITLE_INFO["Title Info + Images<br/>+ List of Venues"]
    TITLE_INFO -- "Picks a venue + date" --> LOAD_SLOTS
    LOAD_SLOTS["GET /listings/{id}/time-slots?date=..."]
    LOAD_SLOTS --> SLOT_DECISION{{"Has hall_id?"}}

    %% === MOVIE/EVENT PATH (Seat Map) ===
    SLOT_DECISION -- "Yes → Movies/Events" --> SEAT_MAP["💺 Seat Map<br/><small>/book/{time_slot_id}/seats</small>"]
    SEAT_MAP -- "GET /time-slots/{id}/seats" --> SELECT_SEATS["Select Seats"]
    SELECT_SEATS -- "POST /time-slots/{id}/seats/lock" --> LOCK_RESULT{{"Lock OK?"}}
    LOCK_RESULT -- "200 OK" --> TIMER["⏱ 10-min Timer Starts"]
    LOCK_RESULT -- "409 Conflict" --> SEAT_ERROR["❌ Seats Unavailable<br/>Pick different seats"]
    SEAT_ERROR --> SELECT_SEATS
    TIMER --> CHECKOUT

    %% === RESTAURANT PATH (Slot + Quantity + Capacity Hold) ===
    SLOT_DECISION -- "No → Restaurants" --> QTY_SLOT["🍽 Pick Quantity<br/>+ Time Slot"]
    QTY_SLOT -- "POST /time-slots/{id}/hold" --> HOLD_RESULT{{"Hold OK?"}}
    HOLD_RESULT -- "200 OK" --> HOLD_TIMER["⏱ 5-min Hold Starts"]
    HOLD_RESULT -- "409 Conflict" --> HOLD_ERROR["❌ Slot Full<br/>Pick different slot"]
    HOLD_ERROR --> QTY_SLOT
    HOLD_TIMER --> CHECKOUT

    %% === EVENT PATH (No Slots) ===
    TITLE_INFO -- "No time slots<br/>(concerts/events)" --> QTY_ONLY["🎫 Pick Quantity Only"]
    QTY_ONLY --> CHECKOUT

    %% === LOGIN WALL ===
    CHECKOUT["📝 Checkout<br/><small>/book/confirm</small>"]
    CHECKOUT --> LOGGED_IN{{"Logged in?"}}
    LOGGED_IN -- "No" --> LOGIN["🔑 Login / Register<br/><small>/login or /register</small>"]
    LOGIN -- "POST /auth/login<br/>or POST /auth/register" --> JWT_STORED["JWT Stored"]
    JWT_STORED --> CHECKOUT
    LOGGED_IN -- "Yes" --> PAY

    PAY["💳 Pay Now (Mock)"]
    PAY -- "POST /bookings" --> BOOKING_RESULT{{"Booking OK?"}}
    BOOKING_RESULT -- "201 Created" --> SUCCESS["✅ Booking Success<br/><small>/book/success/{booking_number}</small>"]
    BOOKING_RESULT -- "409 Conflict<br/>Lock expired / sold out" --> BOOKING_ERROR["❌ Booking Failed<br/>Return to seat map or slots"]
    BOOKING_ERROR --> DETAIL

    SUCCESS --> MY_BOOKINGS["📚 My Bookings<br/><small>/bookings</small>"]
    MY_BOOKINGS -- "GET /bookings?status=upcoming" --> TABS["Upcoming | Past | Cancelled"]
    TABS -- "PATCH /bookings/{id}/cancel" --> CANCELLED["Booking Cancelled<br/>Seats Released"]

    HOME -- "Profile icon" --> PROFILE["👤 Profile<br/><small>/profile</small>"]
    PROFILE -- "GET /auth/me<br/>PATCH /auth/me" --> PROFILE

    %% Styling
    style HOME fill:#4F46E5,color:#fff,stroke:#3730A3
    style BROWSE fill:#4F46E5,color:#fff,stroke:#3730A3
    style DETAIL fill:#7C3AED,color:#fff,stroke:#6D28D9
    style SEAT_MAP fill:#7C3AED,color:#fff,stroke:#6D28D9
    style CHECKOUT fill:#059669,color:#fff,stroke:#047857
    style SUCCESS fill:#059669,color:#fff,stroke:#047857
    style LOGIN fill:#D97706,color:#fff,stroke:#B45309
    style SEAT_ERROR fill:#DC2626,color:#fff,stroke:#B91C1C
    style HOLD_ERROR fill:#DC2626,color:#fff,stroke:#B91C1C
    style BOOKING_ERROR fill:#DC2626,color:#fff,stroke:#B91C1C
    style MY_BOOKINGS fill:#4F46E5,color:#fff,stroke:#3730A3
    style PROFILE fill:#4F46E5,color:#fff,stroke:#3730A3
```

> **Color key:** 🟦 Blue = Browse screens · 🟪 Purple = Detail/selection · 🟩 Green = Booking success · 🟧 Orange = Auth · 🟥 Red = Errors

---

### 🛡️ Admin Flow

```mermaid
flowchart TD
    A_LOGIN["🔑 Admin Login<br/><small>POST /auth/login</small>"]
    A_LOGIN --> A_HOME["🏠 Admin Home<br/><small>/admin</small>"]
    A_HOME -- "GET /admin/dashboard/stats" --> CATEGORY_CARDS["3 Category Cards<br/>Movies | Events | Restaurants<br/><small>with title counts</small>"]

    %% === SIDEBAR NAV ===
    A_HOME --> SIDEBAR{{"Sidebar Nav"}}
    SIDEBAR -- "Dashboard" --> DASHBOARD["📊 Dashboard<br/><small>/admin/dashboard</small><br/>Stats: titles, bookings,<br/>revenue, users"]
    SIDEBAR -- "Venues" --> VENUES
    SIDEBAR -- "Bookings" --> A_BOOKINGS

    %% === TITLE MANAGEMENT ===
    CATEGORY_CARDS -- "Clicks a category" --> TITLES_LIST["📋 Titles List<br/><small>/admin/titles?category=movies</small>"]
    TITLES_LIST -- "GET /titles?category=movies" --> TITLES_TABLE["Table: name, rating,<br/>featured, status, venues"]
    TITLES_TABLE -- "Add Title" --> WIZARD_1
    TITLES_TABLE -- "Edit" --> WIZARD_1_EDIT["Step 1: Edit Title<br/><small>PATCH /admin/titles/{id}</small>"]
    TITLES_TABLE -- "Delete" --> DELETE_TITLE["DELETE /admin/titles/{id}<br/>Cascades to listings"]

    %% === 3-STEP WIZARD ===
    WIZARD_1["✏️ Step 1: Title Info<br/><small>category, title, description,<br/>metadata, tags, is_featured</small>"]
    WIZARD_1 -- "POST /admin/titles" --> TITLE_CREATED["Title Created ✅"]
    TITLE_CREATED -- "POST /admin/titles/{id}/images" --> IMAGES_UPLOADED["Images Uploaded"]
    IMAGES_UPLOADED --> WIZARD_2

    WIZARD_2["🏢 Step 2: Add Venues<br/><small>Multi-select venues,<br/>set price + dates per venue</small>"]
    WIZARD_2 -- "POST /admin/titles/{id}/listings" --> LISTINGS_CREATED["Listings Created ✅<br/><small>One per venue</small>"]
    LISTINGS_CREATED --> NEEDS_SLOTS{{"Needs time slots?"}}

    NEEDS_SLOTS -- "Yes (movies/restaurants)" --> WIZARD_3
    NEEDS_SLOTS -- "No (single events)" --> DONE_TITLE["✅ Title Published"]

    WIZARD_3["⏰ Step 3: Time Slots<br/><small>Per venue: dates, times,<br/>hall (if movie), capacity</small>"]
    WIZARD_3 -- "POST /admin/listings/{id}/time-slots<br/>(bulk per venue)" --> DONE_TITLE

    %% === VENUE MANAGEMENT ===
    VENUES["🏢 Manage Venues<br/><small>/admin/venues</small>"]
    VENUES -- "GET /admin/venues" --> VENUE_TABLE["Table: name, type,<br/>city, capacity"]
    VENUE_TABLE -- "Add Venue<br/>POST /admin/venues" --> VENUE_CREATED["Venue Created ✅"]
    VENUE_TABLE -- "Edit<br/>PATCH /admin/venues/{id}" --> VENUE_TABLE
    VENUE_TABLE -- "Manage Halls" --> HALLS

    HALLS["📺 Manage Halls<br/><small>/admin/venues/{id}/halls</small>"]
    HALLS -- "GET /admin/venues/{id}/halls" --> HALL_TABLE["Table: name,<br/>screen_type, capacity"]
    HALL_TABLE -- "Add Hall<br/>POST /admin/venues/{id}/halls" --> HALL_TABLE
    HALL_TABLE -- "Manage Seats" --> SEATS

    SEATS["💺 Seat Layout Editor<br/><small>/admin/halls/{id}/seats</small>"]
    SEATS -- "POST /admin/halls/{id}/seats/bulk" --> SEAT_GRID["Seat Grid:<br/>rows, categories, prices,<br/>aisle gaps"]

    %% === BOOKING MANAGEMENT ===
    A_BOOKINGS["📦 Manage Bookings<br/><small>/admin/bookings</small>"]
    A_BOOKINGS -- "GET /admin/bookings?page=1&limit=20" --> BOOKING_TABLE["Table: booking_number,<br/>user, title, venue,<br/>date, amount, status"]
    BOOKING_TABLE -- "Click row" --> BOOKING_DETAIL["Booking Detail<br/><small>GET /admin/bookings/{id}</small>"]

    %% Styling
    style A_HOME fill:#4F46E5,color:#fff,stroke:#3730A3
    style DASHBOARD fill:#4F46E5,color:#fff,stroke:#3730A3
    style TITLES_LIST fill:#7C3AED,color:#fff,stroke:#6D28D9
    style WIZARD_1 fill:#059669,color:#fff,stroke:#047857
    style WIZARD_2 fill:#059669,color:#fff,stroke:#047857
    style WIZARD_3 fill:#059669,color:#fff,stroke:#047857
    style DONE_TITLE fill:#059669,color:#fff,stroke:#047857
    style VENUES fill:#D97706,color:#fff,stroke:#B45309
    style HALLS fill:#D97706,color:#fff,stroke:#B45309
    style SEATS fill:#D97706,color:#fff,stroke:#B45309
    style A_BOOKINGS fill:#DC2626,color:#fff,stroke:#B91C1C
    style A_LOGIN fill:#4F46E5,color:#fff,stroke:#3730A3
    style DELETE_TITLE fill:#DC2626,color:#fff,stroke:#B91C1C
```

> **Color key:** 🟦 Blue = Navigation/Dashboard · 🟪 Purple = Title management · 🟩 Green = 3-step creation wizard · 🟧 Orange = Venue/Hall/Seat setup · 🟥 Red = Bookings/Delete
