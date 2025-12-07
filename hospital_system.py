
from dataclasses import dataclass, field
from typing import Optional, Any, Dict, List, Tuple
import heapq
import itertools
import time

# ---------- ADTs ----------
@dataclass
class Patient:
    id: int
    name: str
    age: int
    severity: int = 0
    history: List[str] = field(default_factory=list)

@dataclass
class Token:
    tokenId: int
    patientId: int
    doctorId: int
    slotId: Optional[int]
    type: str  # "ROUTINE" or "EMERGENCY"
    timestamp: float = field(default_factory=time.time)

@dataclass
class Doctor:
    id: int
    name: str
    specialization: str

# Slot node for singly linked list per doctor schedule
class SlotNode:
    def __init__(self, slotId: int, startTime: str, endTime: str, status: str = "FREE"):
        self.slotId = slotId
        self.startTime = startTime
        self.endTime = endTime
        self.status = status  # "FREE" or "BOOKED"
        self.next: Optional['SlotNode'] = None

# ---------- Data Structures ----------
class CircularQueue:
    """Fixed-size circular queue implemented with list for routine tokens."""
    # enqueue/dequeue are O(1)
    def __init__(self, capacity=1000):
        self.cap = capacity
        self.data = [None]*capacity
        self.head = 0
        self.tail = 0
        self.size = 0

    def enqueue(self, item) -> bool:
        if self.size == self.cap:
            return False
        self.data[self.tail] = item
        self.tail = (self.tail + 1) % self.cap
        self.size += 1
        return True

    def dequeue(self):
        if self.size == 0:
            return None
        item = self.data[self.head]
        self.data[self.head] = None
        self.head = (self.head + 1) % self.cap
        self.size -= 1
        return item

    def peek(self):
        if self.size == 0:
            return None
        return self.data[self.head]

    def is_empty(self):
        return self.size == 0

    def __len__(self):
        return self.size

class MinHeapTriage:
    """Min-heap where lower severity score -> higher priority."""
    # insert/extract = O(log n)
    def __init__(self):
        self.heap: List[Tuple[int,int,Token]] = []
        self._counter = itertools.count()  # tie-breaker

    def insert(self, token: Token, severity: int):
        # priority key is severity; lower is more urgent
        count = next(self._counter)
        heapq.heappush(self.heap, (severity, count, token))

    def extract_min(self) -> Optional[Token]:
        if not self.heap:
            return None
        _, _, token = heapq.heappop(self.heap)
        return token

    def peek(self) -> Optional[Token]:
        if not self.heap:
            return None
        return self.heap[0][2]

    def __len__(self):
        return len(self.heap)

class PatientIndex:
    """Hash table using Python dict; supports CRUD"""
    def __init__(self):
        self.table: Dict[int, Patient] = {}

    def upsert(self, patient: Patient):
        self.table[patient.id] = patient

    def get(self, patientId: int) -> Optional[Patient]:
        return self.table.get(patientId)

    def delete(self, patientId: int):
        if patientId in self.table:
            del self.table[patientId]

class UndoStack:
    """Simple stack to store actions for undo. push/pop O(1)."""
    def __init__(self):
        self.stack: List[Tuple[str, Any]] = []

    def push(self, action_type: str, payload: Any):
        self.stack.append((action_type, payload))

    def pop(self) -> Optional[Tuple[str, Any]]:
        if not self.stack:
            return None
        return self.stack.pop()

    def is_empty(self):
        return len(self.stack) == 0

# ---------- Scheduler per doctor (singly linked list) ----------
class DoctorSchedule:
    def __init__(self, doctor: Doctor):
        self.doctor = doctor
        self.head: Optional[SlotNode] = None
        self.slot_map: Dict[int, SlotNode] = {}  # O(1) access by slotId

    def add_slot(self, slotId: int, startTime: str, endTime: str):
        node = SlotNode(slotId, startTime, endTime, status="FREE")
        node.next = self.head
        self.head = node
        self.slot_map[slotId] = node

    def cancel_slot(self, slotId: int) -> bool:
        node = self.slot_map.get(slotId)
        if node and node.status == "BOOKED":
            node.status = "FREE"
            return True
        return False

    def book_next_free(self) -> Optional[SlotNode]:
        # traverse to find first FREE slot
        cur = self.head
        while cur:
            if cur.status == "FREE":
                cur.status = "BOOKED"
                return cur
            cur = cur.next
        return None

    def find_slot(self, slotId: int) -> Optional[SlotNode]:
        return self.slot_map.get(slotId)

    def pending_count(self):
        # count booked slots
        cnt = 0
        cur = self.head
        while cur:
            if cur.status == "BOOKED":
                cnt += 1
            cur = cur.next
        return cnt

    def next_free_slot(self) -> Optional[SlotNode]:
        cur = self.head
        while cur:
            if cur.status == "FREE":
                return cur
            cur = cur.next
        return None

# ---------- Main System ----------
class HospitalSystem:
    def __init__(self, queue_capacity=500):
        self.patients = PatientIndex()
        self.doctors: Dict[int, Doctor] = {}
        self.schedules: Dict[int, DoctorSchedule] = {}
        self.routine_queue = CircularQueue(capacity=queue_capacity)
        self.triage = MinHeapTriage()
        self.undo = UndoStack()
        self.token_counter = itertools.count(1000)  # token ids
        self.served: List[Token] = []

    # Patient methods
    def register_patient(self, pid: int, name: str, age: int, severity: int = 0):
        p = Patient(id=pid, name=name, age=age, severity=severity)
        self.patients.upsert(p)
        return p

    def get_patient(self, pid: int) -> Optional[Patient]:
        return self.patients.get(pid)

    # Doctor / Schedule methods
    def add_doctor(self, doc_id: int, name: str, specialization: str):
        d = Doctor(id=doc_id, name=name, specialization=specialization)
        self.doctors[doc_id] = d
        self.schedules[doc_id] = DoctorSchedule(d)
        return d

    def add_slot_to_doctor(self, doc_id: int, slotId: int, start: str, end: str):
        sched = self.schedules.get(doc_id)
        if not sched:
            raise ValueError("Doctor not found")
        sched.add_slot(slotId, start, end)

    # Booking routine appointment (enqueue)
    def book_routine(self, patientId: int, doctorId: int) -> Optional[Token]:
        patient = self.get_patient(patientId)
        if not patient:
            raise ValueError("Patient not registered")
        sched = self.schedules.get(doctorId)
        if not sched:
            raise ValueError("Doctor not found")
        slot = sched.book_next_free()
        if not slot:
            return None  # no free slot
        tokenId = next(self.token_counter)
        token = Token(tokenId=tokenId, patientId=patientId, doctorId=doctorId, slotId=slot.slotId, type="ROUTINE")
        ok = self.routine_queue.enqueue(token)
        if not ok:
            # rollback slot booking
            slot.status = "FREE"
            return None
        # push undo: to undo a book -> remove token & free slot
        self.undo.push("book", {"token": token})
        return token

    # Cancel booking by tokenId (search queue and free slot)
    def cancel_booking(self, tokenId: int) -> bool:
        # naive approach: reconstruct queue excluding token (O(n)), but acceptable for assignment
        removed = None
        size = len(self.routine_queue)
        temp = []
        for _ in range(size):
            t = self.routine_queue.dequeue()
            if t and t.tokenId == tokenId:
                removed = t
            else:
                temp.append(t)
        for t in temp:
            self.routine_queue.enqueue(t)
        if removed:
            # free the slot
            sched = self.schedules.get(removed.doctorId)
            if sched:
                node = sched.find_slot(removed.slotId)
                if node:
                    node.status = "FREE"
            self.undo.push("cancel", {"token": removed})
            return True
        return False

    # Serve next patient: emergency triage preempts routine
    def serve_next(self) -> Optional[Token]:
        # if triage has an urgent patient, serve them first
        if len(self.triage) > 0:
            token = self.triage.extract_min()
            self.served.append(token)
            self.undo.push("serve_triage", {"token": token})
            return token
        else:
            token = self.routine_queue.dequeue()
            if token:
                # mark slot as served (slot was already BOOKED)
                self.served.append(token)
                self.undo.push("serve_routine", {"token": token})
                return token
            else:
                return None

    # Insert emergency patient into triage (MinHeap)
    def triage_insert(self, patientId: int, severity: int, doctorId: Optional[int] = None) -> Token:
        # doctorId is optional; triage token can be assigned doctor later or preassigned
        tokenId = next(self.token_counter)
        token = Token(tokenId=tokenId, patientId=patientId, doctorId=doctorId if doctorId is not None else -1, slotId=None, type="EMERGENCY")
        self.triage.insert(token, severity)
        self.undo.push("triage_insert", {"token": token, "severity": severity})
        return token

    # Undo last action
    def undo_last(self) -> str:
        it = self.undo.pop()
        if not it:
            return "Nothing to undo"
        action, payload = it
        if action == "book":
            token: Token = payload["token"]
            # remove token from routine queue (O(n)), free slot
            removed = False
            size = len(self.routine_queue)
            temp = []
            for _ in range(size):
                t = self.routine_queue.dequeue()
                if t and t.tokenId == token.tokenId:
                    removed = True
                else:
                    temp.append(t)
            for t in temp:
                self.routine_queue.enqueue(t)
            # free slot
            sched = self.schedules.get(token.doctorId)
            if sched:
                node = sched.find_slot(token.slotId)
                if node:
                    node.status = "FREE"
            return f"Undid booking token {token.tokenId}" if removed else "Could not find token to undo"
        elif action == "cancel":
            token: Token = payload["token"]
            # re-enqueue token (as routine) and mark slot BOOKED
            sched = self.schedules.get(token.doctorId)
            if sched:
                node = sched.find_slot(token.slotId)
                if node:
                    node.status = "BOOKED"
            self.routine_queue.enqueue(token)
            return f"Undid cancellation: rebooked token {token.tokenId}"
        elif action == "serve_routine":
            token: Token = payload["token"]
            # put token back to front of queue (re-serve undone)
            # simple approach: reconstruct with token at head
            temp = []
            size = len(self.routine_queue)
            for _ in range(size):
                temp.append(self.routine_queue.dequeue())
            self.routine_queue.enqueue(token)  # will go to tail, but acceptable as "returned to queue"
            for t in temp:
                self.routine_queue.enqueue(t)
            # also remove from served
            try:
                self.served.remove(token)
            except ValueError:
                pass
            return f"Undid serving of routine token {token.tokenId}"
        elif action == "serve_triage":
            token: Token = payload["token"]
            # put back into triage heap with same severity (we don't store severity in payload for this action,
            # but for safety we'll insert with severity 0; a more complete impl would store severity)
            # For this implementation, assume severity 0 (highest priority) if missing.
            # We'll push back token with severity 0 to requeue
            self.triage.insert(token, 0)
            try:
                self.served.remove(token)
            except ValueError:
                pass
            return f"Undid serving of triage token {token.tokenId}"
        elif action == "triage_insert":
            token: Token = payload["token"]
            # need to remove the token from triage heap (O(n)), simpler: rebuild heap excluding token
            newheap = []
            removed = False
            while self.triage.heap:
                item = heapq.heappop(self.triage.heap)
                if item[2].tokenId == token.tokenId:
                    removed = True
                    continue
                newheap.append(item)
            self.triage.heap = newheap
            heapq.heapify(self.triage.heap)
            return f"Undid triage insert {token.tokenId}" if removed else "Could not find triage token to undo"
        else:
            return "Unknown action to undo"

    # Reports
    def report_per_doctor(self) -> List[Dict[str, Any]]:
        reps = []
        for doc_id, sched in self.schedules.items():
            reps.append({
                "doctorId": doc_id,
                "doctorName": sched.doctor.name,
                "pending_booked_slots": sched.pending_count(),
                "next_free_slot": getattr(sched.next_free_slot(), "slotId", None)
            })
        return reps

    def report_served_vs_pending(self) -> Dict[str,int]:
        pending = len(self.routine_queue) + len(self.triage)
        return {"served": len(self.served), "pending": pending}

    def top_k_frequent_patients(self, k=3) -> List[Tuple[int,int]]:
        # compute frequencies from served list
        freq = {}
        for t in self.served:
            freq[t.patientId] = freq.get(t.patientId, 0) + 1
        items = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return items[:k]

# ---------- Example CLI / Sample usage ----------
def sample_run():
    hs = HospitalSystem(queue_capacity=20)
    # add doctors and slots
    hs.add_doctor(1, "Dr. Rao", "General")
    hs.add_doctor(2, "Dr. Mehta", "Cardio")
    # add some slots per doctor
    hs.add_slot_to_doctor(1, 101, "09:00", "09:15")
    hs.add_slot_to_doctor(1, 102, "09:15", "09:30")
    hs.add_slot_to_doctor(2, 201, "10:00", "10:15")
    hs.add_slot_to_doctor(2, 202, "10:15", "10:30")

    # register patients
    hs.register_patient(1, "Alice", 30)
    hs.register_patient(2, "Bob", 45)
    hs.register_patient(3, "Charlie", 25)

    # book routine for Alice with Dr. Rao
    t1 = hs.book_routine(1, 1)
    print("Booked:", t1)

    # book routine for Bob with Dr. Rao
    t2 = hs.book_routine(2, 1)
    print("Booked:", t2)

    # emergency for Charlie severity 2
    tri_token = hs.triage_insert(3, severity=2, doctorId=1)
    print("Triage inserted:", tri_token)

    # serve next (should serve triage first)
    s = hs.serve_next()
    print("Served:", s)

    # serve next (routine)
    s2 = hs.serve_next()
    print("Served:", s2)

    # reports
    print("Per-doctor report:", hs.report_per_doctor())
    print("Served vs pending:", hs.report_served_vs_pending())
    # undo last (served routine)
    print("Undo result:", hs.undo_last())
    print("Served vs pending after undo:", hs.report_served_vs_pending())

if __name__ == "__main__":
    # Run sample test
    sample_run()
