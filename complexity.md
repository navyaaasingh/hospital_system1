# Complexity Analysis

Generated: 2025-12-07 08:53:46

This document lists time complexity T(n) and space usage for the major methods and data structures
used in the **Hospital Appointment & Triage System** implementation.

## Notation
- `n` = number of patients in the system / items in queues/heaps (context-specific)
- `k` = number of slots in a doctor's schedule (per-doctor)
- `d` = number of doctors
- `u` = number of actions stored in the undo stack
- `m` = number of entries in patient hash table (≈ n)
- `B` = circular queue capacity (fixed, if used)

---

## Data Structures (summary)
- **CircularQueue (fixed-size array)**
  - Operations:
    - `enqueue(item)` — T(n) = O(1) time, Space = O(1) auxiliary; total storage = O(B)
    - `dequeue()` — T(n) = O(1) time, Space = O(1)
    - `peek()` — O(1) time
  - Notes: B is usually set to an expected upper bound on queued routine tokens.

- **MinHeapTriage (heapq)**
  - Operations:
    - `insert(token, severity)` — T(n) = O(log n) time, Space = O(1) auxiliary; total storage = O(n)
    - `extract_min()` — T(n) = O(log n) time, Space = O(1)
    - `peek()` — O(1)
  - Notes: `n` is number of emergency tokens currently in heap.

- **DoctorSchedule (singly linked list of SlotNode)**
  - Operations:
    - `add_slot(slotId, start, end)` — O(1) time (insert at head), Space = O(1)
    - `book_next_free()` — O(k) time worst-case to traverse slots until a free one is found, Space = O(1)
    - `find_slot(slotId)` — O(1) expected if using `slot_map` (dict), otherwise O(k)
    - `pending_count()` — O(k) time, Space = O(1)
  - Notes: `k` is number of slots for that doctor.

- **PatientIndex (Python dict)**
  - Operations:
    - `upsert(patient)` — Average T(n) = O(1), Worst-case T(n) = O(m) (rare, rehash); Space per item = O(1) → total O(m)
    - `get(patientId)` — Average O(1)
    - `delete(patientId)` — Average O(1)

- **UndoStack (list)**
  - Operations:
    - `push(action)` — O(1) time, O(1) space per action
    - `pop()` — O(1)
  - Notes: Some undo operations may perform more expensive operations (e.g., removing a token from the middle of the circular queue) and therefore have higher worst-case cost.

---

## API / Method-Level Complexity

> Methods listed here refer to the member functions in `HospitalSystem`.

### `register_patient(pid, name, age, severity=0)`
- **Time:** O(1) average (inserts into `PatientIndex`)
- **Space:** O(1) auxiliary; adds O(1) to total storage (patient entry) → overall O(m)

### `add_doctor(doc_id, name, specialization)`
- **Time:** O(1)
- **Space:** O(1) auxiliary; adds one `Doctor` and one `DoctorSchedule` → O(d)

### `add_slot_to_doctor(doc_id, slotId, start, end)`
- **Time:** O(1) (inserts new `SlotNode` at head)
- **Space:** O(1) per slot → O(k) total for doctor's schedule

### `book_routine(patientId, doctorId)`
- **Steps:**
  1. patient lookup in hash table — O(1)
  2. schedule lookup — O(1)
  3. `book_next_free()` — O(k) worst-case (traverse slots)
  4. create `Token` and `enqueue()` to CircularQueue — O(1)
  5. push to `UndoStack` — O(1)
- **Time (total):** O(k) worst-case (dominant cost is finding a free slot)
- **Space:** O(1) auxiliary; adds one `Token` to queue → overall storage +1 token

### `cancel_booking(tokenId)`
- **Implementation note:** The provided implementation performs a queue reconstruction to remove a token from the middle of the circular queue.
- **Steps:**
  1. Dequeue all elements (n = current queue length) and re-enqueue excluding the removed token — O(n)
  2. Free slot in schedule — O(1)
  3. Push cancel action to `UndoStack` — O(1)
- **Time:** O(n) worst-case (linear in queue length)
- **Space:** O(n) auxiliary for temporary storage list (unless implemented in-place)

### `triage_insert(patientId, severity, doctorId=None)`
- **Time:** O(log h) where `h` is number of items in triage heap (h ≤ n)
- **Space:** O(1) auxiliary; adds one entry to heap → overall O(h)

### `serve_next()`
- **Behavior:** Emergency patients (heap) are served before routine queue.
- **Steps:**
  - If triage heap not empty:
    - `extract_min()` — O(log h)
  - Else:
    - `dequeue()` from circular queue — O(1)
  - Push serve action to `UndoStack` — O(1)
- **Time:** O(log h) worst-case when serving from heap, otherwise O(1)
- **Space:** O(1) auxiliary

### `undo_last()`
- **Complexity depends on the action being undone:**
  - Undo `book`:
    - Remove token from queue by reconstructing queue — O(n)
    - Free slot — O(1)
  - Undo `cancel`:
    - Re-enqueue token — O(1)
  - Undo `serve_routine`:
    - Re-enqueue token (current implementation appends to tail) — O(n) if trying to put at front (but implementation appends then reorders), worst-case O(n)
  - Undo `serve_triage`:
    - Re-insert into heap — O(log h)
  - Undo `triage_insert`:
    - Rebuild heap excluding token — O(h)
- **Time:** Worst-case O(max(n, h))
- **Space:** May use O(n) or O(h) auxiliary temporary lists during rebuilds

### Reporting Methods
- `report_per_doctor()`:
  - Iterates over `d` doctors and traverses each doctor's slots (k_i per doctor)
  - **Time:** O(sum_k_i) = O(total_slots) = O(d * k) worst-case
  - **Space:** O(d) for collection of report entries
- `report_served_vs_pending()`:
  - Computes `len(served)`, `len(routine_queue)`, `len(triage)` — O(1) each
  - **Time:** O(1)
  - **Space:** O(1)
- `top_k_frequent_patients(k)`:
  - Counts frequencies over `served` list (size s)
  - Sorting frequencies (unique patients p) — O(p log p)
  - **Time:** O(s + p log p)
  - **Space:** O(p)

---

## Possible Improvements (affecting complexity)
1. **Remove tokens from queue in O(1):**
   - Use a doubly-linked list + hashmap from tokenId→node to delete arbitrary tokens in O(1).
   - This would change `cancel_booking` / undo book from O(n) → O(1) time.
2. **Persisting storage:**
   - Using a database (e.g., SQLite) for patients and tokens would move storage costs off memory, but add I/O latency.
3. **Undo optimization:**
   - Store inverse operations with exact positions / severity metadata to avoid expensive rebuilds.
4. **Scalability:**
   - For very large systems, sharding by doctor or using priority queues per department reduces contention and average-case latencies.

---
