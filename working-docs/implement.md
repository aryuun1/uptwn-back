# Database Schema Design — Events & Experiences Discovery Platform

Based on the **District PRD**, this document proposes a complete database schema to support events, movies, restaurants, bookings, users, and the admin panel.

---

## PRD Summary

The platform lets users **discover, browse, and book** different types of titles:

- **Movies** (shows, screenings)
- **Events** (concerts, meetups, etc.)
- **Restaurants / Dining** (reservations)

Key features: User registration/login, listing browsing, booking/reservations, booking history, search, filters, sorting, and admin management.

**Tech Stack:** React JS + FastAPI + PostgreSQL + JWT

---

## Custom Types

```sql
CREATE TYPE category_type AS ENUM ('movies', 'events', 'restaurants');
```

> Categories are hardcoded as a PostgreSQL ENUM rather than a separate table. The frontend renders the category tabs (Movies | Events | Restaurants) from a static list — no API call needed.

---

## Proposed Tables

### 1. `users`
>
> Stores all registered users (both end-users and admins).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Unique user identifier |
| `email` | VARCHAR(255) | UNIQUE, NOT NULL | User's email |
| `password_hash` | VARCHAR(255) | NOT NULL | Hashed password |
| `full_name` | VARCHAR(150) | NOT NULL | User's display name |
| `phone` | VARCHAR(20) | NULLABLE | Phone number |
| `role` | VARCHAR(20) | NOT NULL, DEFAULT 'user' | `user` or `admin` |
| `avatar_url` | TEXT | NULLABLE | Profile image URL |
| `is_active` | BOOLEAN | DEFAULT TRUE | Soft-delete flag |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Registration time |
| `updated_at` | TIMESTAMP | NULLABLE | Last profile update |

---

### 2. `venues`
>
> Stores reusable venue/location info — theatres, event halls, restaurants, etc.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Unique venue ID |
| `name` | VARCHAR(255) | NOT NULL | e.g., "PVR Phoenix Mall" |
| `type` | VARCHAR(50) | NOT NULL | `theater`, `restaurant`, `event_hall`, `outdoor` |
| `address` | TEXT | NULLABLE | Full address |
| `city` | VARCHAR(100) | NOT NULL | City for filtering |
| `latitude` | DECIMAL(10,7) | NULLABLE | Geo coordinate |
| `longitude` | DECIMAL(10,7) | NULLABLE | Geo coordinate |
| `capacity` | INT | NULLABLE | Total venue capacity |
| `amenities` | TEXT[] | NULLABLE | e.g., `{"parking", "ac", "wheelchair_access"}` |
| `contact_phone` | VARCHAR(20) | NULLABLE | Venue contact |
| `image_url` | TEXT | NULLABLE | Venue photo |
| `is_active` | BOOLEAN | DEFAULT TRUE | Soft-delete |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Created timestamp |

---

### 3. `halls`
>
> Screens or halls within a venue — e.g., Screen 1 (IMAX), Screen 2 (Regular). Enables a multiplex to run multiple movies simultaneously in different halls.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Unique hall ID |
| `venue_id` | UUID | FK → venues(id), NOT NULL | Parent venue |
| `name` | VARCHAR(100) | NOT NULL | e.g., "Screen 1", "IMAX Hall", "Screen 3" |
| `screen_type` | VARCHAR(50) | NULLABLE | `imax`, `regular`, `4dx`, `dolby`, `vip` |
| `capacity` | INT | NOT NULL | Total seats in this hall |
| `is_active` | BOOLEAN | DEFAULT TRUE | Soft-delete |

---

### 4. `titles`
>
> **The WHAT** — shared content and identity of a bookable item. A movie, a concert, a restaurant concept. One title can have multiple listings (one per venue).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Unique title ID |
| `category` | category_type | NOT NULL | `movies`, `events`, or `restaurants` |
| `title` | VARCHAR(255) | NOT NULL | e.g., "Interstellar IMAX", "Farzi Cafe Dinner" |
| `slug` | VARCHAR(255) | UNIQUE, NOT NULL | Global URL-friendly slug (e.g., `interstellar-imax`) |
| `description` | TEXT | NULLABLE | Full description |
| `short_description` | VARCHAR(500) | NULLABLE | Card/preview text |
| `image_url` | TEXT | NULLABLE | Main poster/image |
| `duration_minutes` | INT | NULLABLE | Duration (e.g., movie length) |
| `tags` | TEXT[] | NULLABLE | Searchable tags (PostgreSQL array) |
| `metadata` | JSONB | NULLABLE | Category-specific extra data* |
| `rating` | DECIMAL(2,1) | DEFAULT 0.0 | Average rating — maintained by DB trigger on `reviews` table |
| `rating_count` | INT | DEFAULT 0 | Number of ratings — maintained by DB trigger on `reviews` table |
| `is_featured` | BOOLEAN | DEFAULT FALSE | Show on homepage carousel |
| `created_by` | UUID | FK → users(id) | Admin who created it |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Created timestamp |
| `updated_at` | TIMESTAMP | NULLABLE | Last update |
| `is_active` | BOOLEAN | DEFAULT TRUE | Soft-delete |

> [!TIP]
> **Why a single `titles` table?** Instead of separate tables for events, movies, restaurants, etc., a unified table keeps the schema simple. The `category` column is a PostgreSQL ENUM (`movies`, `events`, `restaurants`). Category-specific fields (e.g., `cuisine` for restaurants, `genre` for movies) go into the `metadata` JSONB column.
>
> **Rating lives here** — not on `listings`. If "Interstellar" plays at 20 cinemas, users rate the movie once. All venues show the same rating.

**Example `metadata` values:**

```json
// Movie
{"genre": "Action", "language": "Hindi", "certification": "UA", "director": "XYZ"}

// Restaurant
{"cuisine": "Italian", "meal_type": "Dinner", "veg_nonveg": "Both"}

// Event
{"artist": "Arijit Singh", "genre": "Bollywood"}
```

---

### 5. `listings`
>
> **The WHERE** — a venue-specific instance of a title. "Interstellar at PVR Saket" is one listing; "Interstellar at INOX Nehru Place" is another. Both point to the same title.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Unique listing ID |
| `title_id` | UUID | FK → titles(id), NOT NULL | Parent title (the WHAT) |
| `venue_id` | UUID | FK → venues(id), NULLABLE | Where it takes place (NULL for virtual events) |
| `city` | VARCHAR(100) | NULLABLE | Denormalized from venue for city-filter queries |
| `price` | DECIMAL(10,2) | NULLABLE | Base price at this venue (see price hierarchy) |
| `currency` | VARCHAR(3) | DEFAULT 'INR' | E.g., INR, USD |
| `start_datetime` | TIMESTAMP | NULLABLE | When this listing starts running |
| `end_datetime` | TIMESTAMP | NULLABLE | When it ends |
| `total_capacity` | INT | NULLABLE | Max bookable slots/seats at this venue |
| `status` | VARCHAR(20) | DEFAULT 'active' | `active`, `draft`, `cancelled`, `completed` |
| `created_by` | UUID | FK → users(id) | Admin who created it |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Created timestamp |
| `updated_at` | TIMESTAMP | NULLABLE | Last update |

> Unique constraint on (`title_id`, `venue_id`) — one listing per title per venue.
>
> For categories without venues (e.g., a one-off concert), only one listing is created with `venue_id = NULL`.
>
> `city` is denormalized from the parent venue. Filtering by city without this would require a JOIN to `venues` on every browse query.

---

### 6. `title_images`
>
> Multiple images per title (gallery). Images belong to the title, not individual listings — since the movie poster is the same regardless of venue.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Image ID |
| `title_id` | UUID | FK → titles(id), NOT NULL | Parent title |
| `image_url` | TEXT | NOT NULL | Image URL |
| `display_order` | INT | DEFAULT 0 | Sort order |
| `caption` | VARCHAR(255) | NULLABLE | Image caption |

---

### 7. `time_slots`
>
> **The WHEN** — available booking slots for listings that need time-based booking (shows, reservations).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Slot ID |
| `listing_id` | UUID | FK → listings(id), NOT NULL | Parent listing (venue-specific) |
| `hall_id` | UUID | FK → halls(id), NULLABLE | Which hall/screen this showing is in (movies/events) |
| `slot_date` | DATE | NOT NULL | Date of the slot |
| `start_time` | TIME | NOT NULL | Start time |
| `end_time` | TIME | NULLABLE | End time |
| `capacity` | INT | NOT NULL | Total seats/slots |
| `booked_count` | INT | DEFAULT 0 | Already booked |
| `price_override` | DECIMAL(10,2) | NULLABLE | Slot-specific price (overrides listing price) |
| `is_active` | BOOLEAN | DEFAULT TRUE | Slot available? |

> `hall_id` is NULLABLE — restaurants don't use halls. Only movie/event listings that need a specific screen link to a hall.
>
> **Category-based validation (enforced by the API):** The `POST /admin/listings/{id}/time-slots` endpoint validates `hall_id` against the parent title's category:
>
> - `movies` → `hall_id` is **required**. Rejected with 400 if missing.
> - `restaurants` → `hall_id` is **forbidden**. Rejected with 400 if provided.
> - `events` → `hall_id` is **optional**. Theater events use halls; concerts don't.
>
> The frontend enforces this at the UX level (the hall dropdown is hidden for restaurants, required for movies), but the backend validates independently — **frontend controls the experience, backend enforces the contract.**

---

### 8. `seats`
>
> Individual seats within a hall. Defines the physical seat map — rows, numbers, categories, and layout gaps.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Seat ID |
| `hall_id` | UUID | FK → halls(id), NOT NULL | Which hall this seat belongs to |
| `row_label` | VARCHAR(5) | NOT NULL | e.g., `A`, `B`, `AA` |
| `seat_number` | INT | NOT NULL | e.g., `1`, `2`, `3` |
| `category` | VARCHAR(20) | NOT NULL | `platinum`, `gold`, `silver`, `vip` |
| `price` | DECIMAL(10,2) | NOT NULL | Price for this seat category |
| `is_aisle` | BOOLEAN | DEFAULT FALSE | Gap/empty space in the layout (not a real seat) |
| `is_accessible` | BOOLEAN | DEFAULT FALSE | Wheelchair accessible seat |

> Unique constraint on (`hall_id`, `row_label`, `seat_number`).

---

### 9. `seat_availability`
>
> Tracks the status of every seat for every time slot. This is what the seat map UI reads in real time.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Record ID |
| `time_slot_id` | UUID | FK → time_slots(id), NOT NULL | Which showtime |
| `seat_id` | UUID | FK → seats(id), NOT NULL | Which seat |
| `status` | VARCHAR(20) | DEFAULT 'available' | `available`, `booked`, `locked` |
| `locked_by` | UUID | FK → users(id), NULLABLE | User who temporarily locked this seat |
| `locked_until` | TIMESTAMP | NULLABLE | Lock expiry — auto-releases after 10 minutes |

> Unique constraint on (`time_slot_id`, `seat_id`).
> **Lazy creation:** rows are NOT pre-populated when a time slot is created. A missing row is treated as `available`. Rows are only inserted when a seat is first locked or booked — this avoids inserting 200 rows per slot per show (which explodes to millions of rows across many venues and dates).
> **Lock flow:** user selects seat → `INSERT ... ON CONFLICT DO UPDATE` sets status = `locked`, locked_until = NOW() + 10min → on booking confirm → status = `booked`. Abandoned locks expire via a background job that runs every minute.

---

### 10. `booking_holds`
>
> Temporary capacity holds for quantity-based bookings (restaurants). Prevents overbooking during the checkout window — equivalent of seat locking for restaurants.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Hold ID |
| `user_id` | UUID | FK → users(id), NOT NULL | User who holds the capacity |
| `time_slot_id` | UUID | FK → time_slots(id), NOT NULL | Which slot's capacity is held |
| `quantity` | INT | NOT NULL | Number of spots held |
| `expires_at` | TIMESTAMP | NOT NULL | Hold expiry — auto-releases after 5 minutes |
| `created_at` | TIMESTAMP | DEFAULT NOW() | When the hold was created |

> Unique constraint on (`user_id`, `time_slot_id`) — one hold per user per slot.
>
> **Hold flow:** User enters checkout → `INSERT INTO booking_holds` + increment `time_slots.booked_count` → on booking confirm → delete hold, booking takes over the count → on hold expiry → background job decrements `booked_count` and deletes the hold row.
>
> This table is only used for quantity-based bookings (restaurants). Movie/event bookings use `seat_availability` locking instead.

---

### 11. `bookings`
>
> All user bookings/reservations.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Booking ID |
| `user_id` | UUID | FK → users(id), NOT NULL | Who booked |
| `listing_id` | UUID | FK → listings(id), NOT NULL | What was booked |
| `time_slot_id` | UUID | FK → time_slots(id), NULLABLE | Specific slot (if applicable) |
| `booking_number` | VARCHAR(20) | UNIQUE, NOT NULL | Human-readable booking ref |
| `quantity` | INT | NOT NULL, DEFAULT 1 | Number of tickets/seats |
| `total_amount` | DECIMAL(10,2) | NOT NULL | Total price |
| `status` | VARCHAR(20) | DEFAULT 'confirmed' | `confirmed`, `cancelled`, `completed`, `pending` |
| `booking_date` | TIMESTAMP | DEFAULT NOW() | When the booking was made |
| `event_date` | DATE | NULLABLE | Date of the title event |
| `notes` | TEXT | NULLABLE | Special requests |
| `cancelled_at` | TIMESTAMP | NULLABLE | Cancellation timestamp |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Record creation |

---

### 12. `booking_seats`
>
> Junction table linking a booking to the specific seats the user selected.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Record ID |
| `booking_id` | UUID | FK → bookings(id), NOT NULL | Parent booking |
| `seat_id` | UUID | FK → seats(id), NOT NULL | The selected seat |
| `time_slot_id` | UUID | FK → time_slots(id), NOT NULL | Which showtime this seat was booked for — disambiguates seat bookings across multiple shows |

> Unique constraint on (`booking_id`, `seat_id`).
> `time_slot_id` is included to make direct queries on `booking_seats` unambiguous — without it, seat C3 booked for the 3PM show vs 6PM show would look identical in this table.
> `bookings.quantity` can be derived as `COUNT(booking_seats)` but kept as a convenience field.

---

### 13. `reviews` *(Bonus Feature)*
>
> User ratings and reviews for **titles** (not individual listings). If a movie plays at 20 cinemas, all reviews go to the same title — one shared rating.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Review ID |
| `user_id` | UUID | FK → users(id), NOT NULL | Reviewer |
| `title_id` | UUID | FK → titles(id), NOT NULL | Reviewed title |
| `rating` | INT | NOT NULL, CHECK(1-5) | Star rating |
| `comment` | TEXT | NULLABLE | Review text |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Review date |

> Unique constraint on (`user_id`, `title_id`) — one review per user per title.

---

### 14. `notifications` *(Bonus Feature)*
>
> User notifications for booking confirmations, reminders, etc.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Notification ID |
| `user_id` | UUID | FK → users(id), NOT NULL | Recipient |
| `title` | VARCHAR(255) | NOT NULL | Notification title |
| `message` | TEXT | NOT NULL | Notification body |
| `type` | VARCHAR(50) | NOT NULL | `booking_confirmed`, `reminder`, `cancelled` |
| `is_read` | BOOLEAN | DEFAULT FALSE | Read status |
| `reference_id` | UUID | NULLABLE | Link to booking or listing |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Sent time |

---

## Table Summary

| # | Table | Purpose | Core/Bonus |
|---|-------|---------|------------|
| 1 | `users` | User accounts & admin roles | Core |
| 2 | `venues` | Reusable venue/location data | Core |
| 3 | `halls` | Screens/halls within a venue (multiplex support) | Core |
| 4 | `titles` | The WHAT — shared content, rating, metadata | Core |
| 5 | `listings` | The WHERE — venue-specific instances of titles | Core |
| 6 | `title_images` | Image gallery per title | Core |
| 7 | `time_slots` | The WHEN — booking slots/showtimes (linked to listing + hall) | Core |
| 8 | `seats` | Individual seats within a hall (seat map layout) | Core |
| 9 | `seat_availability` | Per-seat status per time slot (available/locked/booked) | Core |
| 10 | `booking_holds` | Temporary capacity holds for restaurant checkout (5-min TTL) | Core |
| 11 | `bookings` | User booking records | Core |
| 12 | `booking_seats` | Specific seats selected per booking | Core |
| 13 | `reviews` | Ratings & reviews (linked to titles) | Bonus |
| 14 | `notifications` | User notifications | Bonus |

> [!IMPORTANT]
> The **12 core tables** cover all PRD requirements including seat-level selection, multiplex hall support, restaurant capacity holds, and shared ratings across venues. The 2 bonus tables are optional enhancements. Categories are handled by a PostgreSQL ENUM (`category_type`) instead of a separate table.

---

## Required Indexes

Performance-critical indexes to create alongside the schema migrations:

```sql
-- titles (discovery/search hot path)
CREATE INDEX idx_titles_category  ON titles(category);
CREATE INDEX idx_titles_featured  ON titles(is_featured);
CREATE INDEX idx_titles_tags      ON titles USING GIN(tags);
CREATE INDEX idx_titles_search    ON titles USING GIN(to_tsvector('english', title));

-- listings (browse/filter by venue and city)
CREATE INDEX idx_listings_title   ON listings(title_id);
CREATE INDEX idx_listings_city    ON listings(city);
CREATE INDEX idx_listings_status  ON listings(status);

-- time_slots (most frequent join — listing detail + slot picker)
CREATE INDEX idx_time_slots_listing_date ON time_slots(listing_id, slot_date);
CREATE INDEX idx_time_slots_hall         ON time_slots(hall_id);

-- seat_availability (real-time seat map reads — high volume)
CREATE INDEX idx_seat_avail_slot_status  ON seat_availability(time_slot_id, status);
CREATE INDEX idx_seat_avail_lock_expiry  ON seat_availability(locked_until) WHERE status = 'locked';

-- booking_holds (cleanup job finds expired holds)
CREATE INDEX idx_booking_holds_expiry ON booking_holds(expires_at) WHERE expires_at IS NOT NULL;

-- bookings (user history queries)
CREATE INDEX idx_bookings_user_status ON bookings(user_id, status);
CREATE INDEX idx_bookings_listing     ON bookings(listing_id);
```

> [!NOTE]
> `listings.city` is denormalized from the parent venue. Filtering by city on listings without this column would require a JOIN to `venues` on every browse query — a significant performance hit at scale.

---

## Key Design Decisions

1. **`titles` + `listings` split (WHAT vs WHERE)** — `titles` holds the shared content (title, description, metadata, rating) while `listings` holds venue-specific data (price, dates, capacity). A movie at 20 cinemas = 1 title + 20 listings. No content duplication, one shared rating, and updating a typo is a single `PATCH /admin/titles/{id}` — no bulk-update needed.

2. **Hardcoded categories via ENUM** — Categories (`movies`, `events`, `restaurants`) are defined as a PostgreSQL ENUM `category_type`. No categories table, no admin CRUD for categories, no API endpoint. The frontend renders category tabs from a static list. Adding a new category requires a schema migration (`ALTER TYPE category_type ADD VALUE 'new_category'`).

3. **Separate `venues` table** — Avoids duplicating location data across listings. Multiple listings can share the same venue (e.g., a theater with multiple movie showtimes). Admin picks from a dropdown instead of re-entering venue info.

4. **`halls` within `venues`** — A venue (e.g., PVR Phoenix Mall) has multiple screens (Screen 1 IMAX, Screen 2 Regular). Each `time_slot` links to a `hall_id`, so two movies can run simultaneously in different halls of the same multiplex without conflict. `halls` is NULLABLE on `time_slots` — restaurants don't need it.

5. **`time_slots` for flexibility** — Movies have showtimes, restaurants have reservation slots. One table handles all of these.

6. **Seat map via `seats` + `seat_availability`** — `seats` defines the static layout of a hall (rows, numbers, categories, prices). `seat_availability` is the dynamic per-slot status table. Rows are created **lazily** — only when a seat is first locked or booked. A missing row is treated as `available`. This avoids inserting hundreds of rows per showtime across thousands of slots.

7. **Seat locking mechanism (movies/events)** — When a user selects a seat, its `seat_availability.status` is set to `locked` with a `locked_until = NOW() + 10 minutes`. The booking API uses `SELECT ... FOR UPDATE` to prevent two users locking the same seat simultaneously. A background job releases expired locks every minute.

8. **Capacity hold mechanism (restaurants)** — Restaurants don't use seat maps, but they still need protection during checkout. When a user enters checkout, a lightweight capacity hold is created: `booked_count` is temporarily incremented via `UPDATE time_slots SET booked_count = booked_count + :quantity WHERE id = :slot_id AND booked_count + :quantity <= capacity FOR UPDATE`, and a hold record is inserted into a `booking_holds` table (`user_id`, `time_slot_id`, `quantity`, `expires_at = NOW() + 5 minutes`). If the user completes booking within 5 minutes, the hold is converted to a real booking. If the hold expires, the background cleanup job decrements `booked_count` and deletes the hold. This ensures restaurants get the same overbooking protection as movies during the checkout window.

9. **`booking_seats` junction table** — Records exactly which seats belong to a booking. `bookings.quantity` is kept as a convenience field (= `COUNT(booking_seats)`).

10. **`metadata` JSONB** — Category-specific fields (genre, cuisine) live here, avoiding wide sparse columns.

11. **Soft-delete via `is_active`** — No records are permanently deleted.

12. **`booking_number`** — Human-readable reference (e.g., `BK-20260216-001`) separate from the UUID primary key.

13. **Price Hierarchy** — Three sources of price exist; precedence is strictly defined:
    1. `seats.price` — for seat-map bookings (movies/events with halls). Total = SUM of `seats.price` for all selected seats. Each category (Platinum/Gold/Silver) has its own price.
    2. `time_slots.price_override` — overrides listing base price for a specific slot (e.g., weekend surcharge). Used for quantity-based bookings (restaurants).
    3. `listings.price` — base fallback when no slot override is set.
    > **Rule:** if `seat_ids` are provided → use `seats.price`. Else if `time_slots.price_override` is not null → use that. Else use `listings.price`.

14. **Category-to-hall validation** — The booking flow branches on `hall_id` presence (seat map vs quantity picker), not on `category` directly. To prevent misconfiguration, the `POST /admin/listings/{id}/time-slots` endpoint validates `hall_id` against the parent title's category: movies require it, restaurants reject it, events allow it optionally. The frontend hides/shows the hall dropdown based on category (UX layer), while the backend enforces the same rules independently (safety layer).

15. **`booking_number` generation** — Generated atomically inside the booking transaction:

    ```sql
    SELECT 'BK-' || TO_CHAR(NOW(), 'YYYYMMDD') || '-' ||
           LPAD((COUNT(*) + 1)::TEXT, 3, '0')
    FROM bookings
    WHERE DATE(booking_date) = CURRENT_DATE
    FOR UPDATE
    ```

    This produces per-day sequential numbers (001, 002, …) without a separate sequence table. The `FOR UPDATE` lock ensures uniqueness under concurrent bookings.

---

## API Endpoints

### 🔓 Auth (Public)

| # | Method | Endpoint | Description |
|---|--------|----------|-------------|
| 1 | POST | `/auth/register` | Register new user (email, password, full_name) → returns JWT (auto-login) |
| 2 | POST | `/auth/login` | Login → returns JWT access + refresh tokens |
| 3 | POST | `/auth/refresh` | Refresh expired access token |
| 4 | GET | `/auth/me` | Get current logged-in user profile |
| 5 | POST | `/auth/logout` | Invalidate current token (adds `jti` to server-side blacklist) |
| 6 | PATCH | `/auth/me` | Update own profile (full_name, phone, avatar_url) |

---

### 🌐 Public APIs (No JWT required)

> Browsing and discovery endpoints are **public** — users can browse without logging in. JWT is only required for locking seats or creating bookings.

#### Browsing & Discovery

| # | Method | Endpoint | Description |
|---|--------|----------|-------------|
| 7 | GET | `/titles` | Browse all titles (with filters & sorting) |
| 8 | GET | `/titles/{id_or_slug}` | Get title detail — accepts UUID or slug. Returns title + all its listings (venues) + images |
| 9 | GET | `/listings/{id}/time-slots` | Get available time slots for a specific listing (venue) |
| 10 | GET | `/venues/{id}` | Get venue details |

**`GET /titles` query params:**

```
?category=movies
&city=delhi
&date=2026-03-04
&price_min=100&price_max=500
&search=interstellar
&sort_by=newest|price_asc|price_desc|rating
&is_featured=true
&page=1&limit=20
```

### 👤 User APIs (Requires JWT)

#### Seat Map

| # | Method | Endpoint | Description |
|---|--------|----------|-------------|
| 11 | GET | `/time-slots/{id}/seats` | Get full seat map for a time slot (all seats with status: available/locked/booked) |
| 12 | POST | `/time-slots/{id}/seats/lock` | Lock selected seats (body: `seat_ids[]`). Uses `INSERT ... ON CONFLICT DO UPDATE` with row-lock. Returns locked seats or `409 Conflict` |
| 13 | DELETE | `/time-slots/{id}/seats/lock` | Release seat locks for current user (user goes back/cancels) |

#### Capacity Holds (Restaurants)

| # | Method | Endpoint | Description |
|---|--------|----------|-------------|
| 14 | POST | `/time-slots/{id}/hold` | Create a 5-min capacity hold for quantity-based bookings (restaurants). Increments `booked_count`, inserts `booking_holds` row. Returns hold details or `409 Conflict` if insufficient capacity |
| 15 | DELETE | `/time-slots/{id}/hold` | Release capacity hold for current user (user goes back from checkout). Decrements `booked_count`, deletes hold row |

**`POST /time-slots/{id}/hold` request body:**

```json
{ "quantity": 2 }
```

**`POST /time-slots/{id}/hold` response (200 OK):**

```json
{
  "hold_id": "hold-uuid-1",
  "time_slot_id": "slot-uuid-12",
  "quantity": 2,
  "expires_at": "2026-03-04T14:05:00Z",
  "ttl_seconds": 300,
  "remaining_capacity": 18
}
```

**If insufficient capacity (409 Conflict):**

```json
{
  "error": "insufficient_capacity",
  "available": 1,
  "requested": 2,
  "message": "Only 1 spot remaining for this time slot."
}
```

> **Hold validation:** The endpoint checks the parent title's category — only `restaurants` (and `events` without `hall_id`) can use holds. Movies with seat maps must use `/seats/lock` instead. Returns `400: "Use seat locking for this category"` if misused.

**`GET /time-slots/{id}/seats` response:**

```json
{
  "time_slot_id": "uuid",
  "hall": { "name": "Screen 1", "screen_type": "imax" },
  "rows": [
    {
      "label": "A",
      "category": "platinum",
      "price": 500,
      "seats": [
        { "id": "uuid", "number": 1, "status": "available", "is_accessible": false },
        { "id": "uuid", "number": 2, "status": "booked", "is_accessible": false },
        { "id": "uuid", "number": 3, "status": "locked", "is_accessible": false },
        { "id": "uuid", "number": 4, "status": "available", "is_aisle": true }
      ]
    }
  ]
}
```

#### Bookings

| # | Method | Endpoint | Description |
|---|--------|----------|-------------|
| 16 | POST | `/bookings` | Create a new booking |
| 17 | GET | `/bookings` | Get user's booking history (past + upcoming) |
| 18 | GET | `/bookings/{id}` | Get single booking detail |
| 19 | PATCH | `/bookings/{id}/cancel` | Cancel a booking |

**`POST /bookings` request body:**

```json
{
    "listing_id": "uuid",
    "time_slot_id": "uuid | null",
    "seat_ids": ["uuid", "uuid"],
    "quantity": 2,
    "event_date": "2026-03-04",
    "notes": "Window seat please"
}
```

> `seat_ids` is required when the listing uses a seat map (movies/events with halls). For restaurants without a hall, omit `seat_ids` and use `quantity` only.
>
> **Lock validation:** Before committing, the API verifies that `seat_availability.locked_by = current_user.id` AND `locked_until > NOW()` for every seat_id in the request. Returns `409 Conflict` if any seat is not locked by the requesting user or the lock has expired. This prevents users from booking seats they don't hold a lock on.

**`POST /bookings` response:**

```json
{
    "id": "uuid",
    "booking_number": "BK-20260304-001",
    "listing": { "title": "Interstellar IMAX", "image_url": "..." },
    "venue": { "name": "PVR Saket", "city": "Delhi" },
    "time_slot": { "start_time": "15:00", "end_time": "17:00" },
    "quantity": 2,
    "total_amount": 700.00,
    "status": "confirmed"
}
```

**`GET /bookings` query params:**

```
?status=upcoming|past|cancelled
&page=1&limit=10
```

#### Reviews (Bonus)

| # | Method | Endpoint | Description |
|---|--------|----------|-------------|
| 20 | POST | `/titles/{id}/reviews` | Add a review (rating + comment) — rates the title, not an individual listing |
| 21 | GET | `/titles/{id}/reviews` | Get reviews for a title |

#### Notifications (Bonus)

| # | Method | Endpoint | Description |
|---|--------|----------|-------------|
| 22 | GET | `/notifications` | Get user's notifications |
| 23 | PATCH | `/notifications/{id}/read` | Mark notification as read |

---

### 🛡️ Admin APIs (Requires JWT + admin role)

> **First admin account:** Seeded at application startup via `ADMIN_EMAIL` + `ADMIN_PASSWORD` environment variables. The seed script inserts one user with `role = 'admin'` if no admin exists. No self-registration as admin is allowed through the API.

#### Venue Management

| # | Method | Endpoint | Description |
|---|--------|----------|-------------|
| 24 | POST | `/admin/venues` | Create a venue |
| 25 | GET | `/admin/venues` | List all venues |
| 26 | PATCH | `/admin/venues/{id}` | Update venue |
| 27 | DELETE | `/admin/venues/{id}` | Soft-delete venue |

#### Hall Management

| # | Method | Endpoint | Description |
|---|--------|----------|-------------|
| 28 | POST | `/admin/venues/{id}/halls` | Add a hall/screen to a venue |
| 29 | GET | `/admin/venues/{id}/halls` | List halls for a venue |
| 30 | PATCH | `/admin/halls/{id}` | Update hall (name, screen_type, capacity) |
| 31 | DELETE | `/admin/halls/{id}` | Soft-delete a hall |

#### Title Management

| # | Method | Endpoint | Description |
|---|--------|----------|-------------|
| 32 | POST | `/admin/titles` | Create a title (the WHAT — title, description, metadata, tags, category) |
| 33 | PATCH | `/admin/titles/{id}` | Update title content — one update, reflected across all venues |
| 34 | DELETE | `/admin/titles/{id}` | Soft-delete title (cascades to all its listings) |
| 35 | POST | `/admin/titles/{id}/images` | Upload images to title |
| 36 | DELETE | `/admin/titles/{id}/images/{img_id}` | Remove an image |

**`POST /admin/titles` request body:**

```json
{
    "category": "movies",
    "title": "Interstellar IMAX",
    "description": "Christopher Nolan's epic...",
    "short_description": "A team of explorers travel through a wormhole.",
    "duration_minutes": 169,
    "is_featured": true,
    "tags": ["sci-fi", "imax", "nolan"],
    "metadata": { "genre": "Sci-Fi", "language": "English", "certification": "UA", "director": "Christopher Nolan" }
}
```

#### Listing Management (Venue-Specific)

| # | Method | Endpoint | Description |
|---|--------|----------|-------------|
| 37 | POST | `/admin/titles/{id}/listings` | Add venue(s) to a title — accepts array of `{ venue_id, price, start_datetime, end_datetime }`. Creates one listing per venue |
| 38 | PATCH | `/admin/listings/{id}` | Update a listing (venue-specific fields: price, dates, status) |
| 39 | DELETE | `/admin/listings/{id}` | Soft-delete a listing |

**`POST /admin/titles/{id}/listings` request body:**

```json
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

> Backend auto-populates `city` from each venue. Returns array of created listing IDs.
>
> Time slots are managed separately via `POST /admin/listings/{id}/time-slots`. The title is the *what*, the listing is the *where*, time slots are the *when*.

#### Time Slot Management

| # | Method | Endpoint | Description |
|---|--------|----------|-------------|
| 40 | POST | `/admin/listings/{id}/time-slots` | Bulk-add time slots (accepts array). All slots inserted in one transaction |
| 41 | PATCH | `/admin/time-slots/{id}` | Update a time slot |
| 42 | DELETE | `/admin/time-slots/{id}` | Deactivate a time slot |

**`POST /admin/listings/{id}/time-slots` request body (array — supports bulk creation):**

```json
[
  {
    "slot_date": "2026-03-04",
    "start_time": "09:00",
    "end_time": "11:49",
    "capacity": 200,
    "hall_id": "uuid",
    "price_override": null
  },
  {
    "slot_date": "2026-03-04",
    "start_time": "14:00",
    "end_time": "16:49",
    "capacity": 200,
    "hall_id": "uuid",
    "price_override": 400.00
  }
]
```

> **Category-based `hall_id` validation:** The endpoint resolves the parent title's category via `listing → title.category` and enforces:
>
> - `movies` → `hall_id` **required**. Returns `400: "Movies require a hall assignment"` if missing.
> - `restaurants` → `hall_id` **forbidden**. Returns `400: "Restaurants cannot have hall assignments"` if provided.
> - `events` → `hall_id` **optional**. Theater events use halls (seat map); concerts don't (quantity-based).
>
> `price_override` sets a slot-specific price (e.g., weekend surcharge); null falls back to `listings.price`.

#### Seat Map Management

| # | Method | Endpoint | Description |
|---|--------|----------|-------------|
| 43 | POST | `/admin/halls/{id}/seats/bulk` | Bulk-create seat layout for a hall (rows + numbers + categories) |
| 44 | GET | `/admin/halls/{id}/seats` | View all seats in a hall |
| 45 | PATCH | `/admin/seats/{id}` | Update a seat (category, price, accessibility) |
| 46 | DELETE | `/admin/seats/{id}` | Remove a seat from the layout |

#### Booking Management

| # | Method | Endpoint | Description |
|---|--------|----------|-------------|
| 47 | GET | `/admin/bookings` | View all bookings (with filters) |
| 48 | GET | `/admin/bookings/{id}` | View booking detail |

**`GET /admin/bookings` query params:**

```
?listing_id=uuid
&status=confirmed|cancelled|completed
&date_from=2026-03-01&date_to=2026-03-31
&page=1&limit=20
```

#### Dashboard

| # | Method | Endpoint | Description |
|---|--------|----------|-------------|
| 49 | GET | `/admin/dashboard/stats` | Total titles, listings, bookings, revenue, users, counts per category |

---

### API Summary

| Role | Area | Count |
|------|------|-------|
| Public | Auth (register, login, refresh, me, logout, PATCH /me) | 6 |
| Public | Browsing (no JWT) | 4 |
| User | Seat Map (movies/events) | 3 |
| User | Capacity Holds (restaurants) | 2 |
| User | Bookings | 4 |
| User | Reviews (Bonus) | 2 |
| User | Notifications (Bonus) | 2 |
| Admin | Venues | 4 |
| Admin | Halls | 4 |
| Admin | Titles + Images | 5 |
| Admin | Listings (venue assignments) | 3 |
| Admin | Time Slots | 3 |
| Admin | Seat Map | 4 |
| Admin | Bookings | 2 |
| Admin | Dashboard | 1 |
| | **Total** | **49** |

> [!NOTE]
> **Core APIs: 41** (excluding bonus reviews/notifications). These cover all PRD requirements including logout, profile update, slug-based title lookup, multi-venue listing creation, time slot management, restaurant capacity holds, and admin CRUD with hall and seat layout management. Categories are hardcoded — no category APIs needed.

---

## Screen-by-Screen User Journeys

> Full step-by-step flows with all API payloads and response examples are in **[user_journeys.md](file:///c:/Users/Hi/Desktop/work/user_journeys.md)**. Below is a summary of every screen and its APIs.

### 👤 Regular User Screens

| Screen | URL | What User Does | APIs Called |
|--------|-----|---------------|-------------|
| 1. Home | `/` | Lands on homepage, sees featured carousel + category sections | `GET /titles?is_featured=true&limit=10`, `GET /titles?category=movies&sort_by=rating&limit=6`, `GET /titles?category=events&sort_by=newest&limit=6`, `GET /titles?category=restaurants&sort_by=rating&limit=6` |
| 2. Login | `/login` | Enters email + password | `POST /auth/login` |
| 3. Register | `/register` | Fills name/email/password/phone, auto-login | `POST /auth/register` → JWT |
| 4. Browse | `/browse?category=movies&city=delhi` | Filters, sorts, searches, paginates | `GET /titles?category=...&city=...&sort_by=...&page=1&limit=20` |
| 5. Title Detail | `/titles/{slug}` | Views title info, picks venue, picks date/slot | `GET /titles/{slug}`, `GET /listings/{id}/time-slots?date=...` |
| 6. Seat Map | `/book/{time_slot_id}/seats` | Selects and locks seats (movies/events) | `GET /time-slots/{id}/seats`, `POST /time-slots/{id}/seats/lock` |
| 6B. Restaurant Reservation | `/book/{listing_id}/reserve` | Picks time slot, guest count, creates capacity hold (restaurants) | `POST /time-slots/{id}/hold`, `DELETE /time-slots/{id}/hold` |
| 7. Checkout | `/book/confirm` | Reviews summary, clicks "Pay Now" | `POST /bookings` |
| 8. Success | `/book/success/{booking_number}` | Sees confirmation | No API (data from Screen 7) or `GET /bookings/{id}` |
| 9. My Bookings | `/bookings` | Views upcoming/past/cancelled, cancels | `GET /bookings?status=upcoming&page=1`, `PATCH /bookings/{id}/cancel` |
| 10. Profile | `/profile` | Edits name, phone, avatar | `GET /auth/me`, `PATCH /auth/me` |

### 🛡️ Admin Screens

| Screen | URL | What Admin Does | APIs Called |
|--------|-----|----------------|-------------|
| A1. Home | `/admin` | Clicks category card to manage titles | `GET /admin/dashboard/stats` |
| A2. Dashboard | `/admin/dashboard` | Views stats (titles, bookings, revenue, users) | `GET /admin/dashboard/stats` |
| A3. Titles List | `/admin/titles?category=movies` | Views/deletes titles per category | `GET /titles?category=movies`, `DELETE /admin/titles/{id}` |
| A4. Create/Edit Title | `/admin/titles/new?category=movies` | 3-step wizard: title → venues → time slots | `POST /admin/titles`, `POST /admin/titles/{id}/listings`, `POST /admin/listings/{id}/time-slots`, `POST /admin/titles/{id}/images`, `PATCH /admin/titles/{id}`, `PATCH /admin/listings/{id}` |
| A5. Venues | `/admin/venues` | CRUD venues | `GET /admin/venues`, `POST /admin/venues`, `PATCH /admin/venues/{id}`, `DELETE /admin/venues/{id}` |
| A6. Halls | `/admin/venues/{id}/halls` | CRUD halls per venue | `GET/POST /admin/venues/{id}/halls`, `PATCH/DELETE /admin/halls/{id}` |
| A7. Seat Layout | `/admin/halls/{id}/seats` | Manage seat grid | `GET /admin/halls/{id}/seats`, `POST /admin/halls/{id}/seats/bulk`, `PATCH/DELETE /admin/seats/{id}` |
| A8. Bookings | `/admin/bookings` | Views all bookings with filters | `GET /admin/bookings?page=1&limit=20`, `GET /admin/bookings/{id}` |

---

## Edge Cases & Error Handling

| What happens | What the system does |
|-------------|---------------------|
| **Seat lock expires** (10-minute timer runs out) | Frontend redirects back to seat map with a toast message: "Your seat selection expired — please re-select." The locks have already been auto-released by the background job. |
| **Seat already booked/locked by another user** | `POST /seats/lock` returns **409 Conflict** with the list of unavailable seat IDs. Frontend highlights those seats as unavailable and asks the user to pick different ones. |
| **Slot fully booked at booking time** | Backend returns **409 Conflict**. Frontend shows "Sorry, this slot is fully booked" and refreshes the slot list to show updated availability. |
| **JWT expires mid-booking** | Axios interceptor catches the 401, silently calls `POST /auth/refresh`, and retries the original request. If refresh also fails, user is redirected to login. |
| **Network failure between lock and booking** | Locks auto-expire after 10 minutes. User can return to the seat map and re-select. No stale locks persist. |
| **User tries to book seats they didn't lock** | `POST /bookings` returns **409 Conflict**: "Seat selection expired or does not belong to your session." |
| **Restaurant capacity hold expires** (5-minute timer) | Background job decrements `time_slots.booked_count` by the held quantity and deletes the `booking_holds` row. Frontend shows "Your reservation hold expired — please try again." User returns to slot selection. |
| **Restaurant slot fills up during checkout** | The capacity hold prevents this. When user enters checkout, `booked_count` is already incremented. Other users see accurate remaining capacity. If capacity is full, new users get a 409 at the hold step, not at booking. |
| **Admin creates time slot with wrong hall_id for category** | `POST /admin/listings/{id}/time-slots` validates `hall_id` against the parent title's category. Movies require `hall_id`, restaurants reject it, events allow it optionally. Returns **400 Bad Request** on mismatch. |

---

## Admin: First Admin Account

The first admin user is seeded on backend startup using env vars:

```
ADMIN_EMAIL=admin@district.com
ADMIN_PASSWORD=changeme123
```

The seed script inserts this user with `role = 'admin'` only if no admin exists. No API endpoint allows self-promotion to admin.

---

## Discrepancy Check

After applying all changes (rename `experiences` → `titles`, remove `categories` table, add ENUM, renumber, rewrite journeys), the following checks were performed:

### ✅ Schema ↔ API Consistency

| Check | Result |
|-------|--------|
| Every table column is written/read by at least one API | ✅ Pass |
| FK relationships are consistent after renames (`title_id` replaces `experience_id` everywhere) | ✅ Pass |
| `categories` table fully removed — no FK references remain | ✅ Pass |
| `titles.category` uses `category_type` ENUM — no `category_id` FK remains | ✅ Pass |
| ERD matches table definitions | ✅ Pass |

### ✅ API ↔ Journeys Consistency

| Check | Result |
|-------|--------|
| Every screen's API calls exist in the API section | ✅ Pass |
| Every API endpoint is used by at least one screen | ✅ Pass |
| Endpoint numbering is sequential (1–49, no gaps) | ✅ Pass |
| API summary counts match actual endpoints (49 total) | ✅ Pass |
| Table summary count matches actual tables (14 total, 12 core + 2 bonus) | ✅ Pass |
| Category-to-hall_id validation documented on time slot creation API | ✅ Pass |
| Restaurant capacity hold mechanism documented (`booking_holds` table) | ✅ Pass |
