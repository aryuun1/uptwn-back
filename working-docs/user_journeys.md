# Screen-by-Screen User Journeys — Full API Flows

This document walks through every screen in the platform — step by step. For each screen: what the user sees, what they do, which APIs are called, request payloads for POST/PATCH, and response examples for GET.

> **Categories are hardcoded** — the frontend renders Movies | Events | Restaurants from a static list. All browse APIs accept `?category=movies|events|restaurants` as a query param.

---

## 👤 Regular User Screens

---

### Screen 1: Landing / Home Page (`/`)

The user opens the app for the first time (no login required).

**What they see:**

- Hero banner with a search bar
- 3 category tabs: **Movies | Events | Restaurants** (hardcoded, no API)
- Featured titles carousel
- 3 category sections: "Top Movies", "Latest Events", "Top Restaurants"

**What happens on page load — 4 parallel API calls:**

**① Featured carousel:**

```
GET /titles?is_featured=true&limit=10
```

```json
// Response
{
  "data": [
    {
      "id": "uuid-1",
      "category": "movies",
      "title": "Interstellar IMAX",
      "slug": "interstellar-imax",
      "short_description": "A team of explorers travel through a wormhole.",
      "image_url": "https://cdn.example.com/interstellar.jpg",
      "duration_minutes": 169,
      "rating": 4.8,
      "rating_count": 342,
      "is_featured": true,
      "tags": ["sci-fi", "imax", "nolan"],
      "metadata": { "genre": "Sci-Fi", "language": "English", "certification": "UA" }
    }
  ],
  "total": 8,
  "page": 1,
  "limit": 10
}
```

**② Top movies:**

```
GET /titles?category=movies&sort_by=rating&limit=6
```

**③ Latest events:**

```
GET /titles?category=events&sort_by=newest&limit=6
```

**④ Top restaurants:**

```
GET /titles?category=restaurants&sort_by=rating&limit=6
```

> Response format same as ① for all three. Each returns an array of title cards.

**User action:** Clicks a title card → navigates to Screen 5 (`/titles/{slug}`). Clicks a category tab → navigates to Screen 4 (`/browse?category=movies`).

---

### Screen 2: Login (`/login`)

**What they see:** Email + password form, "Register" link.

**User action:** Fills in credentials, clicks "Login".

```
POST /auth/login
```

```json
// Request
{
  "email": "user@example.com",
  "password": "mypassword123"
}
```

```json
// Response (200 OK)
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": "user-uuid",
    "email": "user@example.com",
    "full_name": "Rahul Sharma",
    "role": "user",
    "avatar_url": null
  }
}
```

Frontend stores both tokens. Redirects to `/` (or back to the page they came from).

---

### Screen 3: Register (`/register`)

**What they see:** Full name, email, password, phone fields.

**User action:** Fills in details, clicks "Create Account".

```
POST /auth/register
```

```json
// Request
{
  "full_name": "Rahul Sharma",
  "email": "rahul@example.com",
  "password": "securePass123",
  "phone": "+919876543210"
}
```

```json
// Response (201 Created) — auto-login, same shape as /auth/login
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": "new-user-uuid",
    "email": "rahul@example.com",
    "full_name": "Rahul Sharma",
    "role": "user",
    "avatar_url": null
  }
}
```

Frontend stores token, redirects to `/`.

---

### Screen 4: Browse / Category Page (`/browse?category=movies&city=delhi`)

**What they see:** Filter sidebar, sort dropdown, search bar, paginated title grid.

**On page load (and on every filter/sort/search change):**

```
GET /titles?category=movies&city=delhi&page=1&limit=20
```

**Full query params available:**

```
?category=movies|events|restaurants
&city=delhi
&date=2026-03-04
&price_min=100&price_max=500
&search=interstellar
&sort_by=newest|price_asc|price_desc|rating
&is_featured=true
&page=1&limit=20
```

```json
// Response
{
  "data": [
    {
      "id": "uuid-1",
      "category": "movies",
      "title": "Interstellar IMAX",
      "slug": "interstellar-imax",
      "short_description": "A team of explorers travel through a wormhole.",
      "image_url": "https://cdn.example.com/interstellar.jpg",
      "rating": 4.8,
      "rating_count": 342,
      "duration_minutes": 169,
      "is_featured": true,
      "tags": ["sci-fi", "imax"],
      "metadata": { "genre": "Sci-Fi", "language": "English" },
      "min_price": 200,
      "venue_count": 5,
      "cities": ["delhi", "mumbai"]
    }
  ],
  "total": 47,
  "page": 1,
  "limit": 20,
  "total_pages": 3
}
```

**User actions:**

- Changes a filter → re-fetches `GET /titles` with updated params
- Types in search bar → debounced `GET /titles?search=...`
- Clicks a title card → Screen 5

---

### Screen 5: Title Detail Page (`/titles/{slug}`)

**What they see:** Full title info, image gallery, list of venues, time slot picker.

**On page load:**

```
GET /titles/interstellar-imax
```

```json
// Response
{
  "id": "uuid-1",
  "category": "movies",
  "title": "Interstellar IMAX",
  "slug": "interstellar-imax",
  "description": "Christopher Nolan's epic space exploration drama...",
  "short_description": "A team of explorers travel through a wormhole.",
  "image_url": "https://cdn.example.com/interstellar.jpg",
  "duration_minutes": 169,
  "rating": 4.8,
  "rating_count": 342,
  "tags": ["sci-fi", "imax", "nolan"],
  "metadata": { "genre": "Sci-Fi", "language": "English", "certification": "UA", "director": "Christopher Nolan" },
  "is_featured": true,
  "images": [
    { "id": "img-1", "image_url": "https://cdn.example.com/inter-1.jpg", "display_order": 1, "caption": "Official Poster" },
    { "id": "img-2", "image_url": "https://cdn.example.com/inter-2.jpg", "display_order": 2, "caption": "Behind the scenes" }
  ],
  "listings": [
    {
      "id": "listing-uuid-1",
      "venue": { "id": "venue-uuid-1", "name": "PVR Saket", "city": "Delhi", "type": "theater", "image_url": "..." },
      "price": 350.00,
      "currency": "INR",
      "start_datetime": "2026-03-04T00:00:00",
      "end_datetime": "2026-03-10T23:59:59",
      "status": "active"
    },
    {
      "id": "listing-uuid-2",
      "venue": { "id": "venue-uuid-2", "name": "INOX Nehru Place", "city": "Delhi", "type": "theater", "image_url": "..." },
      "price": 300.00,
      "currency": "INR",
      "start_datetime": "2026-03-04T00:00:00",
      "end_datetime": "2026-03-10T23:59:59",
      "status": "active"
    }
  ]
}
```

**User picks a venue (PVR Saket) and a date → loads time slots:**

```
GET /listings/listing-uuid-1/time-slots?date=2026-03-04
```

```json
// Response
{
  "listing_id": "listing-uuid-1",
  "date": "2026-03-04",
  "time_slots": [
    {
      "id": "slot-uuid-1",
      "hall": { "id": "hall-uuid-1", "name": "Screen 1", "screen_type": "imax" },
      "start_time": "09:00",
      "end_time": "11:49",
      "capacity": 200,
      "booked_count": 45,
      "price_override": null
    },
    {
      "id": "slot-uuid-2",
      "hall": { "id": "hall-uuid-1", "name": "Screen 1", "screen_type": "imax" },
      "start_time": "14:00",
      "end_time": "16:49",
      "capacity": 200,
      "booked_count": 120,
      "price_override": 400.00
    },
    {
      "id": "slot-uuid-3",
      "hall": { "id": "hall-uuid-2", "name": "Screen 2", "screen_type": "regular" },
      "start_time": "18:00",
      "end_time": "20:49",
      "capacity": 150,
      "booked_count": 30,
      "price_override": null
    }
  ]
}
```

**User action:**

- If time slot has a `hall` → clicks slot → Screen 6 (seat map) — **movies/events**
- If time slot has NO `hall` → clicks slot → Screen 6B (restaurant reservation) — **restaurants**
- If no time slots exist (concerts) → clicks "Book Now" → Screen 7 (quantity only)

---

### Screen 6: Seat Map (`/book/{time_slot_id}/seats`) — Movies/Events only

**What they see:** Visual seat grid with rows, categories, colors, and statuses.

**On page load:**

```
GET /time-slots/slot-uuid-2/seats
```

```json
// Response
{
  "time_slot_id": "slot-uuid-2",
  "hall": { "name": "Screen 1", "screen_type": "imax" },
  "rows": [
    {
      "label": "A",
      "category": "platinum",
      "price": 500,
      "seats": [
        { "id": "seat-1", "number": 1, "status": "available", "is_aisle": false, "is_accessible": false },
        { "id": "seat-2", "number": 2, "status": "booked", "is_aisle": false, "is_accessible": false },
        { "id": "seat-3", "number": 3, "status": "available", "is_aisle": false, "is_accessible": false },
        { "id": "seat-4", "number": 4, "status": "locked", "is_aisle": false, "is_accessible": false },
        { "id": "seat-5", "number": 5, "status": "available", "is_aisle": true, "is_accessible": false }
      ]
    },
    {
      "label": "C",
      "category": "gold",
      "price": 350,
      "seats": [
        { "id": "seat-41", "number": 1, "status": "available", "is_aisle": false, "is_accessible": false },
        { "id": "seat-42", "number": 2, "status": "available", "is_aisle": false, "is_accessible": false },
        { "id": "seat-43", "number": 3, "status": "available", "is_aisle": false, "is_accessible": false }
      ]
    }
  ]
}
```

**User selects seats C3, C4 → clicks "Lock Seats":**

```
POST /time-slots/slot-uuid-2/seats/lock
```

```json
// Request
{ "seat_ids": ["seat-43", "seat-44"] }
```

```json
// Response (200 OK)
{
  "locked_seats": ["seat-43", "seat-44"],
  "locked_until": "2026-03-04T14:10:00Z",
  "ttl_seconds": 600
}
```

Frontend starts a **10-minute countdown timer**. User proceeds to Screen 7.

**If seats are already taken:**

```json
// Response (409 Conflict)
{
  "error": "seats_unavailable",
  "unavailable_seat_ids": ["seat-44"],
  "message": "One or more seats are no longer available."
}
```

Frontend highlights those seats as unavailable. User picks different seats.

**If user goes back (cancels):**

```
DELETE /time-slots/slot-uuid-2/seats/lock
```

```json
// Response (200 OK)
{ "released_seats": ["seat-43", "seat-44"] }
```

---

### Screen 6B: Restaurant Reservation (`/book/{listing_id}/reserve`) — Restaurants only

**What they see:** Selected restaurant info (name, image, venue), date picker (pre-filled from Screen 5), available time slots as selectable chips (e.g., "7:00 PM", "7:30 PM", "8:00 PM"), a guest count selector (1–10), and a "Reserve" button.

**On page load — time slots already loaded from Screen 5:**

The time slots were fetched on Screen 5 via `GET /listings/{id}/time-slots?date=2026-03-04`. Restaurants have **no `hall`** in the response — this is what triggers the restaurant path.

```json
// Time slots for a restaurant (already loaded from Screen 5)
{
  "listing_id": "listing-uuid-5",
  "date": "2026-03-04",
  "time_slots": [
    {
      "id": "slot-uuid-10",
      "hall": null,
      "start_time": "19:00",
      "end_time": "20:30",
      "capacity": 50,
      "booked_count": 42,
      "price_override": null
    },
    {
      "id": "slot-uuid-11",
      "hall": null,
      "start_time": "19:30",
      "end_time": "21:00",
      "capacity": 50,
      "booked_count": 50,
      "price_override": null
    },
    {
      "id": "slot-uuid-12",
      "hall": null,
      "start_time": "20:00",
      "end_time": "21:30",
      "capacity": 50,
      "booked_count": 30,
      "price_override": 1200.00
    }
  ]
}
```

Frontend renders:

- **7:00 PM** — 8 spots left (shown as "Available")
- **7:30 PM** — greyed out, "Fully Booked" (`booked_count == capacity`)
- **8:00 PM** — 20 spots left, shows ₹1,200 instead of base price (`price_override`)

**User selects 8:00 PM slot, picks 2 guests, clicks "Reserve":**

This creates a **5-minute capacity hold** — the restaurant equivalent of seat locking for movies.

```
POST /time-slots/slot-uuid-12/hold
Authorization: Bearer <jwt>
```

```json
// Request
{ "quantity": 2 }
```

```json
// Response (200 OK)
{
  "hold_id": "hold-uuid-1",
  "time_slot_id": "slot-uuid-12",
  "quantity": 2,
  "expires_at": "2026-03-04T14:05:00Z",
  "ttl_seconds": 300,
  "remaining_capacity": 18
}
```

Frontend starts a **5-minute countdown timer**. User proceeds to Screen 7 (checkout).

> **What happened on the backend:** `booked_count` was incremented from 30 → 32 via `UPDATE time_slots SET booked_count = booked_count + 2 WHERE id = slot-uuid-12 AND booked_count + 2 <= capacity FOR UPDATE`. A `booking_holds` row was inserted. Other users now see 18 spots remaining — the hold is reflected immediately.

**If slot doesn't have enough capacity:**

```json
// Response (409 Conflict)
{
  "error": "insufficient_capacity",
  "available": 1,
  "requested": 2,
  "message": "Only 1 spot remaining for this time slot."
}
```

Frontend shows the error. User can reduce guest count or pick a different slot.

**If user changes date — re-fetch slots:**

```
GET /listings/listing-uuid-5/time-slots?date=2026-03-05
```

Returns fresh time slots for the new date. Same response format as above.

**If user goes back (cancels the reservation hold):**

```
DELETE /time-slots/slot-uuid-12/hold
Authorization: Bearer <jwt>
```

```json
// Response (200 OK)
{
  "released_quantity": 2,
  "time_slot_id": "slot-uuid-12"
}
```

Backend decrements `booked_count` from 32 → 30 and deletes the `booking_holds` row. Spots are immediately available to other users.

**If the hold expires (user doesn't complete checkout within 5 minutes):**

The background cleanup job (runs every minute) finds expired holds (`expires_at < NOW()`), decrements `booked_count`, deletes the hold row. Frontend shows a toast: "Your reservation hold expired — please try again" and redirects back to this screen.

---

### Screen 7: Booking Confirmation / Checkout (`/book/confirm`)

**What they see:** Summary (title, venue, date/time, seats or quantity, total price), special requests field, "Pay Now" button.

**User clicks "Pay Now" (mock payment):**

**For seat-map bookings (movies/events):**

```
POST /bookings
```

```json
// Request
{
  "listing_id": "listing-uuid-1",
  "time_slot_id": "slot-uuid-2",
  "seat_ids": ["seat-43", "seat-44"],
  "quantity": 2,
  "event_date": "2026-03-04",
  "notes": "Prefer aisle seats"
}
```

**For quantity-based bookings (restaurants — with time slot):**

> **Capacity hold:** Before reaching this screen, the restaurant flow creates a 5-minute capacity hold via `POST /time-slots/{id}/hold` (body: `{ "quantity": 1 }`). This increments `booked_count` and inserts a `booking_holds` row. The checkout screen shows a 5-minute countdown. On booking confirm, the hold is converted to a real booking. On expiry, the background job releases the hold.

```
POST /bookings
```

```json
// Request
{
  "listing_id": "listing-uuid-5",
  "time_slot_id": "slot-uuid-10",
  "quantity": 1,
  "event_date": "2026-03-04",
  "notes": "Anniversary dinner, window seat please"
}
```

**For quantity-based bookings (events — no time slot):**

```
POST /bookings
```

```json
// Request
{
  "listing_id": "listing-uuid-8",
  "quantity": 5,
  "event_date": "2026-03-15"
}
```

```json
// Response (201 Created) — same for all booking types
{
  "id": "booking-uuid",
  "booking_number": "BK-20260304-042",
  "listing": {
    "title": "Interstellar IMAX",
    "image_url": "https://cdn.example.com/interstellar.jpg"
  },
  "venue": { "name": "PVR Saket", "city": "Delhi" },
  "time_slot": { "slot_date": "2026-03-04", "start_time": "14:00", "end_time": "16:49" },
  "seats": [
    { "row": "C", "number": 3, "category": "gold", "price": 350 },
    { "row": "C", "number": 4, "category": "gold", "price": 350 }
  ],
  "quantity": 2,
  "total_amount": 700.00,
  "status": "confirmed",
  "notes": "Prefer aisle seats"
}
```

Redirects to Screen 8.

---

### Screen 8: Booking Success (`/book/success/{booking_number}`)

**What they see:** Booking number, title, venue, date/time, seats, amount, "View My Bookings" button.

**No API call needed** — data is passed from Screen 7 response. Fallback:

```
GET /bookings/booking-uuid
```

(Same response shape as POST /bookings response above.)

---

### Screen 9: My Bookings (`/bookings`)

**What they see:** 3 tabs — Upcoming | Past | Cancelled. Each card shows title image, name, venue, date, booking_number, amount, status.

**On page load (default: upcoming tab):**

```
GET /bookings?status=upcoming&page=1&limit=10
```

**Switching tabs:**

```
GET /bookings?status=past&page=1&limit=10
GET /bookings?status=cancelled&page=1&limit=10
```

```json
// Response
{
  "data": [
    {
      "id": "booking-uuid",
      "booking_number": "BK-20260304-042",
      "listing": {
        "title": "Interstellar IMAX",
        "image_url": "https://cdn.example.com/interstellar.jpg",
        "category": "movies"
      },
      "venue": { "name": "PVR Saket", "city": "Delhi" },
      "time_slot": { "slot_date": "2026-03-04", "start_time": "14:00", "end_time": "16:49" },
      "quantity": 2,
      "total_amount": 700.00,
      "status": "confirmed",
      "booking_date": "2026-03-01T10:30:00Z",
      "event_date": "2026-03-04",
      "seats": [
        { "row": "C", "number": 3, "category": "gold" },
        { "row": "C", "number": 4, "category": "gold" }
      ]
    }
  ],
  "total": 4,
  "page": 1,
  "limit": 10
}
```

**User clicks "Cancel" on an upcoming booking → confirm dialog → confirms:**

```
PATCH /bookings/booking-uuid/cancel
```

```json
// Response (200 OK)
{
  "id": "booking-uuid",
  "booking_number": "BK-20260304-042",
  "status": "cancelled",
  "cancelled_at": "2026-03-02T15:45:00Z"
}
```

Behind the scenes: seats are released back to `available`, `booked_count` decremented.

---

### Screen 10: User Profile (`/profile`)

**What they see:** View/edit full_name, phone, avatar.

**On page load:**

```
GET /auth/me
```

```json
// Response
{
  "id": "user-uuid",
  "email": "rahul@example.com",
  "full_name": "Rahul Sharma",
  "phone": "+919876543210",
  "avatar_url": null,
  "role": "user",
  "created_at": "2026-02-01T10:00:00Z"
}
```

**User edits name and phone → clicks "Save":**

```
PATCH /auth/me
```

```json
// Request
{
  "full_name": "Rahul K. Sharma",
  "phone": "+919876543211"
}
```

```json
// Response (200 OK)
{
  "id": "user-uuid",
  "email": "rahul@example.com",
  "full_name": "Rahul K. Sharma",
  "phone": "+919876543211",
  "avatar_url": null,
  "role": "user"
}
```

---

## 🛡️ Admin Screens

---

### Screen A1: Admin Home (`/admin`)

**What the admin sees:** 3 large category cards — Movies | Events | Restaurants — each showing count of titles. Sidebar: Dashboard, Venues, Bookings.

**On page load:**

```
GET /admin/dashboard/stats
```

```json
// Response
{
  "total_titles": 87,
  "total_bookings": 1420,
  "total_revenue": 2850000.00,
  "total_users": 3200,
  "categories": {
    "movies": { "count": 45 },
    "events": { "count": 28 },
    "restaurants": { "count": 14 }
  }
}
```

**Admin clicks "Movies" card →** navigates to Screen A3 (`/admin/titles?category=movies`).

---

### Screen A2: Admin Dashboard (`/admin/dashboard`)

**What the admin sees:** Stats cards (total titles, bookings, revenue, users), summary charts.

**On page load:** Same API as A1.

```
GET /admin/dashboard/stats
```

(Response same as above.)

---

### Screen A3: Titles List for a Category (`/admin/titles?category=movies`)

**What the admin sees:** Table of titles filtered by category. Columns: name, rating, is_featured, status, # venues, actions (edit/delete). "Add Title" button.

**On page load:**

```
GET /titles?category=movies
```

> Same public browse API — admin sees ALL statuses including `draft`. Response format same as Screen 4.

**Admin clicks "Delete" on a title:**

```
DELETE /admin/titles/uuid-1
```

```json
// Response (200 OK)
{ "id": "uuid-1", "is_active": false, "message": "Title soft-deleted. All linked listings deactivated." }
```

**Admin clicks "Add Title" →** Screen A4 with `?category=movies` pre-filled.
**Admin clicks "Edit" →** Screen A4 (`/admin/titles/{id}/edit`).

---

### Screen A4: Create/Edit Title (`/admin/titles/new?category=movies` or `/admin/titles/{id}/edit`)

This is a **3-step wizard**. The admin completes each step sequentially.

#### Step 1 — Title Info

**Admin fills in:** category (pre-filled), title, description, short_description, duration, tags, metadata (dynamic per category), is_featured.

```
POST /admin/titles
```

```json
// Request
{
  "category": "movies",
  "title": "Interstellar IMAX",
  "description": "Christopher Nolan's epic space exploration drama...",
  "short_description": "A team of explorers travel through a wormhole.",
  "duration_minutes": 169,
  "is_featured": true,
  "tags": ["sci-fi", "imax", "nolan"],
  "metadata": {
    "genre": "Sci-Fi",
    "language": "English",
    "certification": "UA",
    "director": "Christopher Nolan"
  }
}
```

```json
// Response (201 Created)
{
  "id": "new-title-uuid",
  "category": "movies",
  "title": "Interstellar IMAX",
  "slug": "interstellar-imax",
  "is_featured": true,
  "created_at": "2026-03-01T10:00:00Z"
}
```

**Upload images (optional, after title created):**

```
POST /admin/titles/new-title-uuid/images
Content-Type: multipart/form-data
```

```json
// Response (201 Created)
{
  "images": [
    { "id": "img-uuid-1", "image_url": "https://cdn.example.com/uploaded1.jpg", "display_order": 1 }
  ]
}
```

**For edit mode:**

```
PATCH /admin/titles/new-title-uuid
```

```json
// Request (only changed fields)
{ "description": "Updated description...", "is_featured": false }
```

```json
// Response (200 OK)
{ "id": "new-title-uuid", "title": "Interstellar IMAX", "description": "Updated description...", "is_featured": false }
```

#### Step 2 — Add Venues (Create Listings)

**Admin picks venues from a multi-select list.** Sets price + date range per venue.

```
POST /admin/titles/new-title-uuid/listings
```

```json
// Request — array, one per venue
[
  {
    "venue_id": "pvr-saket-uuid",
    "price": 350.00,
    "start_datetime": "2026-03-04T00:00:00",
    "end_datetime": "2026-03-10T23:59:59"
  },
  {
    "venue_id": "inox-nehru-uuid",
    "price": 300.00,
    "start_datetime": "2026-03-04T00:00:00",
    "end_datetime": "2026-03-10T23:59:59"
  }
]
```

```json
// Response (201 Created)
{
  "listings": [
    { "id": "listing-uuid-1", "venue": { "name": "PVR Saket", "city": "Delhi" }, "price": 350.00 },
    { "id": "listing-uuid-2", "venue": { "name": "INOX Nehru Place", "city": "Delhi" }, "price": 300.00 }
  ]
}
```

> Backend auto-populates `city` from each venue.

**For edit mode:**

```
PATCH /admin/listings/listing-uuid-1
```

```json
// Request
{ "price": 400.00, "end_datetime": "2026-03-15T23:59:59" }
```

#### Step 3 — Add Time Slots (per venue)

**Admin clicks into each listing (venue) and adds showtimes for that venue's halls.**

For PVR Saket:

```
POST /admin/listings/listing-uuid-1/time-slots
```

```json
// Request — array, bulk creation
[
  {
    "slot_date": "2026-03-04",
    "start_time": "09:00",
    "end_time": "11:49",
    "capacity": 200,
    "hall_id": "hall-uuid-1",
    "price_override": null
  },
  {
    "slot_date": "2026-03-04",
    "start_time": "14:00",
    "end_time": "16:49",
    "capacity": 200,
    "hall_id": "hall-uuid-1",
    "price_override": 400.00
  },
  {
    "slot_date": "2026-03-04",
    "start_time": "18:00",
    "end_time": "20:49",
    "capacity": 150,
    "hall_id": "hall-uuid-2",
    "price_override": null
  }
]
```

```json
// Response (201 Created)
{
  "time_slots": [
    { "id": "slot-uuid-1", "hall": { "name": "Screen 1" }, "start_time": "09:00", "end_time": "11:49" },
    { "id": "slot-uuid-2", "hall": { "name": "Screen 1" }, "start_time": "14:00", "end_time": "16:49" },
    { "id": "slot-uuid-3", "hall": { "name": "Screen 2" }, "start_time": "18:00", "end_time": "20:49" }
  ]
}
```

> For **restaurants**: omit `hall_id` — the backend rejects `hall_id` with `400: "Restaurants cannot have hall assignments"`. For **movies**: `hall_id` is required — the backend rejects with `400: "Movies require a hall assignment"` if missing. For **events**: `hall_id` is optional (theater events use halls, concerts don't). Skip Step 3 entirely for events with no time slots.
>
> The admin wizard enforces this at the UI level: the hall dropdown is hidden for restaurants and required for movies. The backend validates independently — **frontend controls the experience, backend enforces the contract.**

---

### Screen A5: Manage Venues (`/admin/venues`)

**What the admin sees:** Table of venues — name, type, city, capacity, actions. "Add Venue" button.

**On page load:**

```
GET /admin/venues
```

```json
// Response
{
  "data": [
    {
      "id": "venue-uuid-1",
      "name": "PVR Saket",
      "type": "theater",
      "city": "Delhi",
      "capacity": 800,
      "halls_count": 4,
      "is_active": true
    },
    {
      "id": "venue-uuid-2",
      "name": "Farzi Cafe CP",
      "type": "restaurant",
      "city": "Delhi",
      "capacity": 75,
      "halls_count": 0,
      "is_active": true
    }
  ]
}
```

**Admin clicks "Add Venue":**

```
POST /admin/venues
```

```json
// Request
{
  "name": "PVR Phoenix Mall",
  "type": "theater",
  "city": "Mumbai",
  "address": "Phoenix Mall, Lower Parel, Mumbai",
  "capacity": 1000,
  "amenities": ["parking", "ac", "wheelchair_access"],
  "contact_phone": "+912233445566",
  "image_url": "https://cdn.example.com/pvr-phoenix.jpg"
}
```

```json
// Response (201 Created)
{ "id": "new-venue-uuid", "name": "PVR Phoenix Mall", "type": "theater", "city": "Mumbai" }
```

**Admin clicks "Edit":**

```
PATCH /admin/venues/venue-uuid-1
```

```json
// Request
{ "capacity": 850, "contact_phone": "+911122334455" }
```

**Admin clicks "Delete":**

```
DELETE /admin/venues/venue-uuid-1
```

```json
// Response (200 OK)
{ "id": "venue-uuid-1", "is_active": false }
```

---

### Screen A6: Manage Halls (`/admin/venues/{id}/halls`)

**What the admin sees:** Halls for a specific venue. Table: name, screen_type, capacity, actions. "Add Hall" button.

**On page load:**

```
GET /admin/venues/venue-uuid-1/halls
```

```json
// Response
{
  "venue": { "id": "venue-uuid-1", "name": "PVR Saket" },
  "halls": [
    { "id": "hall-uuid-1", "name": "Screen 1", "screen_type": "imax", "capacity": 200, "is_active": true },
    { "id": "hall-uuid-2", "name": "Screen 2", "screen_type": "regular", "capacity": 150, "is_active": true }
  ]
}
```

**Admin clicks "Add Hall":**

```
POST /admin/venues/venue-uuid-1/halls
```

```json
// Request
{ "name": "Screen 3", "screen_type": "4dx", "capacity": 100 }
```

```json
// Response (201 Created)
{ "id": "hall-uuid-3", "name": "Screen 3", "screen_type": "4dx", "capacity": 100 }
```

**Admin clicks "Edit":**

```
PATCH /admin/halls/hall-uuid-1
```

```json
// Request
{ "name": "Screen 1 — IMAX", "capacity": 220 }
```

**Admin clicks "Delete":**

```
DELETE /admin/halls/hall-uuid-1
```

**Admin clicks "Manage Seats" →** Screen A7.

---

### Screen A7: Manage Seat Layout (`/admin/halls/{id}/seats`)

**What the admin sees:** Visual seat grid editor — rows, seat numbers, categories, prices, aisle gaps.

**On page load:**

```
GET /admin/halls/hall-uuid-1/seats
```

```json
// Response
{
  "hall": { "id": "hall-uuid-1", "name": "Screen 1", "screen_type": "imax", "capacity": 200 },
  "rows": [
    {
      "label": "A",
      "seats": [
        { "id": "seat-1", "number": 1, "category": "platinum", "price": 500, "is_aisle": false, "is_accessible": false },
        { "id": "seat-2", "number": 2, "category": "platinum", "price": 500, "is_aisle": false, "is_accessible": false },
        { "id": "seat-5", "number": 5, "category": "platinum", "price": 500, "is_aisle": true, "is_accessible": false }
      ]
    }
  ]
}
```

**Admin bulk-creates seats (first-time setup):**

```
POST /admin/halls/hall-uuid-1/seats/bulk
```

```json
// Request
{
  "seats": [
    { "row_label": "A", "seat_number": 1, "category": "platinum", "price": 500, "is_aisle": false, "is_accessible": false },
    { "row_label": "A", "seat_number": 2, "category": "platinum", "price": 500, "is_aisle": false, "is_accessible": false },
    { "row_label": "A", "seat_number": 5, "category": "platinum", "price": 500, "is_aisle": true, "is_accessible": false },
    { "row_label": "C", "seat_number": 1, "category": "gold", "price": 350, "is_aisle": false, "is_accessible": false },
    { "row_label": "G", "seat_number": 1, "category": "silver", "price": 200, "is_aisle": false, "is_accessible": true }
  ]
}
```

```json
// Response (201 Created)
{ "created_count": 5, "hall_id": "hall-uuid-1" }
```

**Admin updates a single seat:**

```
PATCH /admin/seats/seat-1
```

```json
// Request
{ "category": "vip", "price": 800 }
```

**Admin deletes a seat:**

```
DELETE /admin/seats/seat-1
```

---

### Screen A8: Manage Bookings (`/admin/bookings`)

**What the admin sees:** Table of all bookings — booking_number, user, title, venue, date, amount, status. Filters: by title/status/date range.

**On page load:**

```
GET /admin/bookings?page=1&limit=20
```

**With filters:**

```
GET /admin/bookings?status=confirmed&date_from=2026-03-01&date_to=2026-03-31&page=1&limit=20
```

```json
// Response
{
  "data": [
    {
      "id": "booking-uuid",
      "booking_number": "BK-20260304-042",
      "user": { "id": "user-uuid", "full_name": "Rahul Sharma", "email": "rahul@example.com" },
      "listing": {
        "title": "Interstellar IMAX",
        "category": "movies"
      },
      "venue": { "name": "PVR Saket", "city": "Delhi" },
      "time_slot": { "slot_date": "2026-03-04", "start_time": "14:00" },
      "quantity": 2,
      "total_amount": 700.00,
      "status": "confirmed",
      "booking_date": "2026-03-01T10:30:00Z",
      "seats": [
        { "row": "C", "number": 3, "category": "gold" },
        { "row": "C", "number": 4, "category": "gold" }
      ]
    }
  ],
  "total": 1420,
  "page": 1,
  "limit": 20,
  "total_pages": 71
}
```

**Admin clicks a row → booking detail:**

```
GET /admin/bookings/booking-uuid
```

(Returns same shape as a single item from the array above, with full details.)

---

## Edge Cases & Error Handling

| Scenario | What Happens |
|----------|-------------|
| **Seat lock expires** (10 min) | Frontend redirects back to seat map: "Your seat selection expired — please re-select." Background job has already released locks. |
| **Seat taken by another user** | `POST /seats/lock` → `409 Conflict` with `unavailable_seat_ids`. Frontend highlights + asks user to pick again. |
| **Slot fully booked** | `POST /bookings` → `409 Conflict`: "This slot is fully booked." Frontend refreshes slot list. |
| **JWT expires mid-booking** | Axios interceptor catches `401`, calls `POST /auth/refresh` silently, retries request. If refresh fails → redirect to login. |
| **Network failure after lock** | Locks auto-expire in 10 min. User can return and re-select. |
| **User books unlocked seats** | `POST /bookings` → `409 Conflict`: "Seat selection expired or does not belong to your session." |
| **Restaurant capacity hold expires** (5 min) | Background job decrements `time_slots.booked_count` and deletes the `booking_holds` row. Frontend shows: "Your reservation hold expired — please try again." User returns to slot selection. |
| **Restaurant slot fills during checkout** | Capacity hold prevents this. `booked_count` is incremented when user enters checkout, so other users see accurate remaining capacity. New users get `409` at the hold step, not at booking. |
| **Admin assigns hall to restaurant** | `POST /admin/listings/{id}/time-slots` validates `hall_id` against parent title's category → `400: "Restaurants cannot have hall assignments"`. |
| **Admin omits hall for movie** | `POST /admin/listings/{id}/time-slots` → `400: "Movies require a hall assignment"`. |
