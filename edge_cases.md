
# Edge Case Test Scenarios

1. Booking with no free slots → expect None
2. Booking an unregistered patient → expect ValueError
3. Cancel nonexistent token → expect False
4. Triage insert with missing doctor → token doctorId = -1
5. serve_next() on empty queues → expect None
6. Heap tie-breaking (equal severity) → FIFO behavior
7. undo_last() when stack empty → "Nothing to undo"
8. Queue reconstruction correctness after cancel
9. Multi-step undo sequence correctness
10. top_k_frequent_patients with k > served_count → return available only
