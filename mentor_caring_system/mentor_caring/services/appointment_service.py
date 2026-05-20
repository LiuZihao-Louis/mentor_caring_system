from __future__ import annotations

from mentor_caring.models import Appointment
from mentor_caring.services.base import BaseService
from mentor_caring.services.utils import require_non_blank


class AppointmentService(BaseService):
    def book_appointment(self, student_id: str, appointment_id: str) -> Appointment:
        student_id = require_non_blank(student_id, "student_id")
        self.store.students.require(student_id, "student")
        appointment_id = require_non_blank(appointment_id, "appointment_id")
        appt = self.store.appointments.require(appointment_id, "appointment")
        if appt.student_id != student_id:
            raise PermissionError("appointment does not belong to this student")
        if appt.status != "available":
            raise ValueError("appointment is not available")
        appt.update_status("booked")
        self.notify(appt.mentor_id, f"Appointment {appointment_id} booked by {student_id}", "appointment", appointment_id)
        self.log(student_id, "book appointment", f"Booked {appointment_id}", student_id=student_id)
        return appt
