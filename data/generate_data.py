"""
Generates realistic mock Indian citizen data for three department systems
(Health, Education, Welfare) in DIFFERENT formats/schemas, deliberately
including overlapping citizens (with slight variations in name spelling,
phone formatting, and address wording) to demonstrate cross-department
duplicate/record-linkage detection.

Run: python generate_data.py
Outputs CSVs into this data/ folder.
"""
import csv
import random

random.seed(42)

# ---- Base "real" citizen identities (the ground truth people) ----
# These will be scattered across departments with format variations.
BASE_PEOPLE = [
    dict(name="Ramesh Kumar Yadav", dob="1985-04-12", gender="M", phone="9876543210",
         address="H.No 12, Sector 15, Rohini, Delhi - 110085", aadhaar_last4="4321"),
    dict(name="Sunita Devi", dob="1990-08-23", gender="F", phone="9123456780",
         address="House No 45, Sector 9, Chandigarh - 160009", aadhaar_last4="8765"),
    dict(name="Mohammed Aslam Sheikh", dob="1978-01-05", gender="M", phone="9988776655",
         address="Flat 302, Green Park Rd, Andheri West, Mumbai - 400058", aadhaar_last4="1122"),
    dict(name="Priya Sharma", dob="1995-11-30", gender="F", phone="8899001122",
         address="Plot 7, Jubilee Hills Rd No 3, Hyderabad - 500033", aadhaar_last4="3344"),
    dict(name="Anil Kumar Singh", dob="1982-06-17", gender="M", phone="7788990011",
         address="Village Bhagwanpur, Post Office Roorkee, Haridwar - 247667", aadhaar_last4="5566"),
    dict(name="Lakshmi Narayanan", dob="1988-03-09", gender="F", phone="9445566778",
         address="No 21, Gandhi Street, T Nagar, Chennai - 600017", aadhaar_last4="7788"),
    dict(name="Deepak Chandra Joshi", dob="1975-12-25", gender="M", phone="9412345678",
         address="H No 8, Rajpur Road, Dehradun - 248001", aadhaar_last4="9900"),
    dict(name="Farida Begum", dob="1992-07-14", gender="F", phone="9308001122",
         address="Mohalla Rasoolpur, Near Idgah, Lucknow - 226003", aadhaar_last4="1234"),
    dict(name="Vikram Aditya Rathore", dob="1980-09-02", gender="M", phone="9001122334",
         address="Bungalow 5, Civil Lines, Jaipur - 302006", aadhaar_last4="2345"),
    dict(name="Kavita Patel", dob="1998-02-28", gender="F", phone="9825566778",
         address="B-14, Satellite Road, Ahmedabad - 380015", aadhaar_last4="3456"),
    dict(name="Suresh Babu Reddy", dob="1970-05-19", gender="M", phone="9848012345",
         address="Door No 3-4-56, Ameerpet, Hyderabad - 500016", aadhaar_last4="4567"),
    dict(name="Anjali Verma", dob="1993-10-11", gender="F", phone="9911223344",
         address="H.No 22, Sector 62, Noida - 201301", aadhaar_last4="5678"),
]

FIRST_NAMES_M = ["Rahul","Amit","Sanjay","Vijay","Arjun","Rohit","Manoj","Ashok","Ravi","Naveen"]
FIRST_NAMES_F = ["Neha","Pooja","Rekha","Meena","Divya","Kiran","Shalini","Geeta","Nisha","Swati"]
SURNAMES = ["Gupta","Mehta","Nair","Das","Chauhan","Bhatt","Iyer","Malhotra","Kulkarni","Pillai",
            "Bansal","Thakur","Menon","Saxena","Dubey"]
CITIES = [
    ("Sector 21, Dwarka, Delhi - 110075"), ("MG Road, Bengaluru - 560001"),
    ("Camp Area, Pune - 411001"), ("Salt Lake, Kolkata - 700064"),
    ("Vastrapur, Ahmedabad - 380015"), ("Alambagh, Lucknow - 226005"),
    ("Chandni Chowk, Delhi - 110006"), ("Kankarbagh, Patna - 800020"),
    ("Panampilly Nagar, Kochi - 682036"), ("Indiranagar, Bengaluru - 560038"),
]

def random_extra_people(n, seed_offset=0):
    people = []
    for i in range(n):
        r = random.Random(1000 + seed_offset + i)
        male = r.random() < 0.5
        fname = r.choice(FIRST_NAMES_M if male else FIRST_NAMES_F)
        sname = r.choice(SURNAMES)
        people.append(dict(
            name=f"{fname} {sname}",
            dob=f"19{r.randint(70,99)}-{r.randint(1,12):02d}-{r.randint(1,28):02d}",
            gender="M" if male else "F",
            phone=f"9{r.randint(100000000,999999999)}",
            address=r.choice(CITIES),
            aadhaar_last4=f"{r.randint(1000,9999)}",
        ))
    return people

ALL_PEOPLE = BASE_PEOPLE + random_extra_people(18)

def name_variant(name, style):
    """Produce a realistic spelling/format variant of a name for a given dept."""
    if style == "title_prefix":
        prefix = random.choice(["Mr.", "Mrs.", "Ms.", "Shri", "Smt."])
        return f"{prefix} {name}"
    if style == "upper":
        return name.upper()
    if style == "initials":
        parts = name.split()
        if len(parts) >= 2:
            return f"{parts[0][0]}. {' '.join(parts[1:])}"
        return name
    if style == "swap":
        parts = name.split()
        if len(parts) >= 2:
            return f"{parts[-1]} {' '.join(parts[:-1])}"
        return name
    return name

def phone_variant(phone, style):
    if style == "country_code":
        return f"+91-{phone}"
    if style == "spaced":
        return f"{phone[:5]} {phone[5:]}"
    if style == "dashed":
        return f"{phone[:3]}-{phone[3:6]}-{phone[6:]}"
    return phone

def address_variant(addr, style):
    if style == "abbrev":
        return (addr.replace("House No", "H.No").replace("Sector", "Sec")
                    .replace("Road", "Rd"))
    if style == "expand":
        return (addr.replace("H.No", "House Number").replace("Sec", "Sector")
                    .replace("Rd", "Road"))
    if style == "lower":
        return addr.lower()
    return addr


# ---------------- HEALTH DEPARTMENT (ABHA-style health registry) ----------------
def gen_health():
    rows = []
    for idx, p in enumerate(ALL_PEOPLE):
        # ~70% of citizens appear in health records
        if random.random() > 0.72:
            continue
        rows.append({
            "abha_id": f"ABHA-{10000+idx}",
            "patient_full_name": name_variant(p["name"], random.choice(["title_prefix", "upper", None, None])),
            "date_of_birth": p["dob"],
            "sex": p["gender"],
            "mobile_no": phone_variant(p["phone"], random.choice(["country_code", "spaced", None, None])),
            "residential_address": address_variant(p["address"], random.choice(["abbrev", "expand", None])),
            "aadhaar_last4": p["aadhaar_last4"],
            "blood_group": random.choice(["A+","B+","O+","AB+","O-","A-"]),
            "vaccination_status": random.choice(["Fully Vaccinated","Partially Vaccinated","Not Vaccinated"]),
            "last_visit_facility": random.choice(["PHC Rohini","District Hospital","CHC Roorkee","AIIMS OPD","Govt Dispensary"]),
            "scheme_enrolled": random.choice(["Ayushman Bharat","State Health Scheme","None"]),
        })
    with open("health_department.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return rows


# ---------------- EDUCATION DEPARTMENT (student/scholarship registry) ----------------
def gen_education():
    rows = []
    for idx, p in enumerate(ALL_PEOPLE):
        if random.random() > 0.55:
            continue
        rows.append({
            "student_id": f"EDU{20000+idx}",
            "StudentName": name_variant(p["name"], random.choice(["initials", "swap", None, None])),
            "DOB": p["dob"],
            "Gender": p["gender"],
            "ContactNumber": phone_variant(p["phone"], random.choice(["dashed", None, None])),
            "GuardianAddress": address_variant(p["address"], random.choice(["lower", "abbrev", None])),
            "AadhaarLast4": p["aadhaar_last4"],
            "School_College": random.choice(["Govt Sr Sec School","State Polytechnic","District Degree College","Kendriya Vidyalaya"]),
            "Class_Course": random.choice(["Class 10","Class 12","B.A. 2nd Year","B.Sc. 1st Year","Diploma - CS"]),
            "ScholarshipStatus": random.choice(["Approved","Pending","Rejected","Not Applied"]),
        })
    with open("education_department.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return rows


# ---------------- WELFARE DEPARTMENT (pension/subsidy/beneficiary registry) ----------------
def gen_welfare():
    rows = []
    for idx, p in enumerate(ALL_PEOPLE):
        if random.random() > 0.5:
            continue
        rows.append({
            "beneficiary_ref": f"WEL-{idx:04d}-{random.randint(100,999)}",
            "full_name": name_variant(p["name"], random.choice(["upper", "title_prefix", None])),
            "birth_date": p["dob"],
            "gender_code": p["gender"],
            "phone_no": phone_variant(p["phone"], random.choice(["spaced", "country_code", None])),
            "address_full": address_variant(p["address"], random.choice(["expand", None])),
            "aadhaar_l4": p["aadhaar_last4"],
            "scheme_name": random.choice(["PM-KISAN","Old Age Pension","Widow Pension","LPG Subsidy","Disability Allowance"]),
            "beneficiary_status": random.choice(["Active","Suspended","Under Verification","Closed"]),
            "monthly_benefit_inr": random.choice([500,1000,1500,2000,3000]),
        })
    with open("welfare_department.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return rows


if __name__ == "__main__":
    h = gen_health()
    e = gen_education()
    w = gen_welfare()
    print(f"Generated: health={len(h)} education={len(e)} welfare={len(w)} rows")
