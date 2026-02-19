# Product Requirements Document (PRD)

## Events & Experiences Discovery Platform (Uptown/District)

### 1. Project Overview

The **Events & Experiences Discovery Platform** is a comprehensive web application designed to allow users to discover, browse, and book various types of entertainment and dining experiences. The platform supports three main categories of "titles":

* **Movies:** Film screenings at theaters.
* **Events:** Concerts, meetups, workshops, and other gatherings.
* **Restaurants:** Dining reservations.

The system aims to provide a seamless user experience for browsing content, viewing venue details, selecting seats or tables, and managing bookings. On the backend, it requires a robust administration interface for managing venues, halls, titles, listings, and showtimes.

### 2. Technical Stack

* **Backend Framework:** FastAPI (Python)
* **Database:** PostgreSQL
* **Authentication:** JWT (JSON Web Tokens)
* **Frontend:** React JS (presumed based on context)
* **Infrastructure:** Containerized (Docker support implied for deployment)

### 3. Functional Requirements

#### 3.1 Authentication & User Management

* **Registration:** Users must be able to register with email, password, and full name.
* **Login:** Secure login using email and password, returning Access and Refresh tokens (JWT).
* **Profile Management:** Users can view and update their profile details (name, phone, avatar).
* **Role-Based Access Control (RBAC):**
  * **End User:** standard access to browse and book.
  * **Admin:** elevated access to manage platform data (venues, titles, listings).

#### 3.2 Browsing & Discovery

* **Unified Search:** Users can search for movies, events, and restaurants by title or keyword.
* **Filtering:**
  * **Category:** Movies, Events, Restaurants.
  * **Location:** City-based filtering.
  * **Date:** Filter by availability on specific dates.
  * **Price:** Range filtering (min/max).
* **Sorting:** Sort results by Newest, Price (Low/High), and Rating.
* **Title Details:** Rich detail pages for each title, including description, images (gallery), duration, and metadata (genre, cuisine, etc.).

#### 3.3 Venues & Listings

* **Multi-Venue Support:** A single title (e.g., "Inception") can be listed at multiple venues (e.g., "PVR Saket", "INOX Nehru Place").
* **Venue Details:** Users can view venue information including address, amenities, and contact info.
* **Showtimes/Slots:** Users can view available time slots for a specific title at a specific venue.

#### 3.4 Booking System

The booking flow varies by category but unifies under a central booking system.

* **Seat Selection (Movies & Seated Events):**
  * Interactive seat map displaying available, booked, and locked seats.
  * Real-time seat locking to prevent double-booking (10-minute lock duration).
  * Support for multiple seat categories (e.g., Platinum, Gold, Silver) with different pricing.
* **Capacity Booking (Restaurants & General Entry Events):**
  * Quantity-based booking without specific seat assignment.
  * Temporary capacity holds (5-minute duration) during the checkout process to ensure availability.
* **Booking Management:**
  * Users can view their booking history (Upcoming, Past, Cancelled).
  * Users can cancel bookings (subject to policy).
  * Unique, human-readable booking reference numbers (e.g., `BK-20260304-001`).

#### 3.5 Reviews & Ratings (Bonus Feature)

* **Title Ratings:** Users can rate and review **titles** (not individual listings).
* **Aggregated Scoring:** The platform displays an average rating for each title based on user reviews.

#### 3.6 Notifications (Bonus Feature)

* System notifications for booking confirmations, cancellations, and reminders.

### 4. Admin Module Requirements

The Admin Panel provides full CRUD (Create, Read, Update, Delete) capabilities for platform management.

#### 4.1 Venue & Hall Management

* **Venues:** Manage venue details (Name, City, Location, Type).
* **Halls:** Manage screens/halls within a venue, including defining seat layouts (Rows, Columns, Categories).

#### 4.2 Title Management

* **Content Management:** Create and edit Titles with rich metadata.
  * *Movies:* Duration, Genre, Language, Certification.
  * *Restaurants:* Cuisine, Meal Type.
  * *Events:* Artist, Genre.
* **Gallery:** Upload and manage images for titles.

#### 4.3 Listing & Inventory Management

* **Listings:** Assign Titles to Venues to create Listings.
* **Time Slots:** specific showtimes or reservation slots for listings.
  * Support for bulk creation of time slots.
  * Price overrides for specific slots (e.g., weekend pricing).

#### 4.4 Booking Administration

* View all user bookings with status and details.
* Dashboard with high-level statistics (Total Bookings, Revenue, Active Users).

### 5. Non-Functional Requirements

#### 5.1 Performance

* **Database Indexing:** Critical fields (search tags, dates, cities) must be indexed for fast retrieval.
* **Concurrency:** The system must handle concurrent booking attempts gracefully using database-level locking (optimistic or pessimistic locking for seats).
* **Scalability:** The architecture should support horizontal scaling (stateless backend).

#### 5.2 Security

* **Data Protection:** Passwords must be hashed (e.g., bcrypt).
* **Token Security:** JWTs must have expiration times; Refresh tokens should be securely managed.
* **Validation:** Strict input validation to prevent injection attacks and ensure data integrity.

#### 5.3 Reliability

* **Transactional Integrity:** Booking operations (locking seats, creating booking records) must be atomic transactions to prevent data inconsistencies.
* **Soft Deletes:** Records (Users, Titles, Venues) should typically be soft-deleted (`is_active=False`) rather than permanently removed to preserve history.

### 6. Database Schema Summary

The system relies on a relational database (PostgreSQL) with the following core entities:

* **Users:** System users and admins.
* **Venues & Halls:** Physical locations and their sub-units.
* **Titles:** The core content entities (Movies, Events, Restaurants).
* **Listings:** The intersection of Titles and Venues.
* **Time Slots:** Specific instances of a Listing available for booking.
* **Seats & Seat Availability:** Layout definitions and real-time inventory status.
* **Bookings:** Transactional records of user reservations.

---
*Drafted based on `implement.md` and project constraints.*
