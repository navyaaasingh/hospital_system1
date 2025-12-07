
import pytest
from src.hospital_system import HospitalSystem, Token

def setup_simple_system():
    hs = HospitalSystem(queue_capacity=10)
    hs.add_doctor(1, "Dr. Rao", "General")
    hs.add_slot_to_doctor(1, 101, "09:00", "09:15")
    hs.add_slot_to_doctor(1, 102, "09:15", "09:30")
    hs.register_patient(1, "Alice", 30)
    hs.register_patient(2, "Bob", 45)
    hs.register_patient(3, "Charlie", 25)
    return hs

def test_book_and_serve_routine():
    hs = setup_simple_system()
    t1 = hs.book_routine(1, 1)
    t2 = hs.book_routine(2, 1)
    assert t1 is not None and t2 is not None
    served1 = hs.serve_next()
    assert isinstance(served1, Token) and served1.patientId == t1.patientId
    served2 = hs.serve_next()
    assert isinstance(served2, Token) and served2.patientId == t2.patientId
    assert hs.serve_next() is None

def test_triage_preempts_routine():
    hs = setup_simple_system()
    t1 = hs.book_routine(1,1)
    tri = hs.triage_insert(3, severity=0, doctorId=1)
    s = hs.serve_next()
    assert isinstance(s, Token) and s.patientId == 3
    s2 = hs.serve_next()
    assert s2.patientId == t1.patientId

def test_cancel_booking_and_undo():
    hs = setup_simple_system()
    t = hs.book_routine(1,1)
    ok = hs.cancel_booking(t.tokenId)
    assert ok is True
    res = hs.undo_last()
    assert "rebooked" in res or "Undid cancellation" in res
    s = hs.serve_next()
    assert s.patientId == t.patientId

def test_undo_serve_triage():
    hs = setup_simple_system()
    tri_token = hs.triage_insert(3, severity=1, doctorId=1)
    s = hs.serve_next()
    assert s.patientId == 3
    res = hs.undo_last()
    assert "Undid serving" in res
    s2 = hs.serve_next()
    assert s2.patientId == 3

def test_report_and_top_k():
    hs = setup_simple_system()
    hs.book_routine(1,1)
    hs.book_routine(2,1)
    hs.triage_insert(3, severity=1, doctorId=1)
    hs.serve_next()
    hs.serve_next()
    rep = hs.report_served_vs_pending()
    assert isinstance(rep, dict)
    top = hs.top_k_frequent_patients(k=2)
    assert isinstance(top, list)
