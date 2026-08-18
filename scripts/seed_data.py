"""Optional: pre-populate a couple of appointments for demo realism."""

from src.mock_api import book_appointment, list_appointments, reset_store

if __name__ == "__main__":
    reset_store()
    
    book_appointment(
        customer_name="Jordan Lee",
        phone="555-0101",
        vehicle="2021 Toyota Camry",
        service="oil change",
        datetime_str="",  
    )
    print("Seed script is mainly a placeholder. The mock API auto-generates open slots.")
    print("Current appointments:", list_appointments())
