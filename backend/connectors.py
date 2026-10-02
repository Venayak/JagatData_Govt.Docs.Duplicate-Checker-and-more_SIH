"""
JagatData - Department connectors.

Each department publishes data in its own legacy format (different column names,
casing, ID schemes). A connector maps a raw dataframe into the COMMON CITIZEN SCHEMA:

    name, dob, gender, phone, address, aadhaar_last4, source_ref_id, extra (dict)

This demonstrates "mapping into a common citizen/business schema" without
needing to replace any legacy department system.
"""
import pandas as pd

COMMON_FIELDS = ["name", "dob", "gender", "phone", "address", "aadhaar_last4", "source_ref_id"]


class ConnectorError(Exception):
    pass


def _validate_row(row: dict) -> list:
    """Basic data-quality validation. Returns list of issues (empty = clean)."""
    issues = []
    if not row.get("name") or len(str(row.get("name")).strip()) < 2:
        issues.append("missing_or_invalid_name")
    if not row.get("dob"):
        issues.append("missing_dob")
    else:
        try:
            pd.to_datetime(row["dob"])
        except Exception:
            issues.append("invalid_dob_format")
    phone = str(row.get("phone") or "")
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) < 10:
        issues.append("invalid_phone")
    if not row.get("address"):
        issues.append("missing_address")
    return issues


def map_health(df: pd.DataFrame) -> pd.DataFrame:
    mapped = pd.DataFrame({
        "name": df.get("patient_full_name"),
        "dob": df.get("date_of_birth"),
        "gender": df.get("sex"),
        "phone": df.get("mobile_no"),
        "address": df.get("residential_address"),
        "aadhaar_last4": df.get("aadhaar_last4"),
        "source_ref_id": df.get("abha_id"),
    })
    extra_cols = [c for c in df.columns if c not in
                  ["patient_full_name", "date_of_birth", "sex", "mobile_no",
                   "residential_address", "aadhaar_last4", "abha_id"]]
    mapped["extra"] = df[extra_cols].to_dict(orient="records") if extra_cols else [{}] * len(df)
    return mapped


def map_education(df: pd.DataFrame) -> pd.DataFrame:
    mapped = pd.DataFrame({
        "name": df.get("StudentName"),
        "dob": df.get("DOB"),
        "gender": df.get("Gender"),
        "phone": df.get("ContactNumber"),
        "address": df.get("GuardianAddress"),
        "aadhaar_last4": df.get("AadhaarLast4"),
        "source_ref_id": df.get("student_id"),
    })
    extra_cols = [c for c in df.columns if c not in
                  ["StudentName", "DOB", "Gender", "ContactNumber",
                   "GuardianAddress", "AadhaarLast4", "student_id"]]
    mapped["extra"] = df[extra_cols].to_dict(orient="records") if extra_cols else [{}] * len(df)
    return mapped


def map_welfare(df: pd.DataFrame) -> pd.DataFrame:
    mapped = pd.DataFrame({
        "name": df.get("full_name"),
        "dob": df.get("birth_date"),
        "gender": df.get("gender_code"),
        "phone": df.get("phone_no"),
        "address": df.get("address_full"),
        "aadhaar_last4": df.get("aadhaar_l4"),
        "source_ref_id": df.get("beneficiary_ref"),
    })
    extra_cols = [c for c in df.columns if c not in
                  ["full_name", "birth_date", "gender_code", "phone_no",
                   "address_full", "aadhaar_l4", "beneficiary_ref"]]
    mapped["extra"] = df[extra_cols].to_dict(orient="records") if extra_cols else [{}] * len(df)
    return mapped


CONNECTOR_REGISTRY = {
    "Health": map_health,
    "Education": map_education,
    "Welfare": map_welfare,
}


def run_connector(department: str, df: pd.DataFrame):
    """
    Maps a raw department dataframe to the common schema, validates rows,
    and returns (clean_records: list[dict], quality_report: dict)
    """
    if department not in CONNECTOR_REGISTRY:
        raise ConnectorError(f"No connector registered for department '{department}'")

    mapper = CONNECTOR_REGISTRY[department]
    mapped_df = mapper(df)

    clean_records = []
    issues_summary = {}
    failed_rows = 0

    for _, row in mapped_df.iterrows():
        row_dict = row.to_dict()
        issues = _validate_row(row_dict)
        if issues:
            failed_rows += 1
            for issue in issues:
                issues_summary[issue] = issues_summary.get(issue, 0) + 1
            row_dict["_issues"] = issues
        else:
            row_dict["_issues"] = []
        clean_records.append(row_dict)

    quality_report = {
        "department": department,
        "total_rows": len(mapped_df),
        "clean_rows": len(mapped_df) - failed_rows,
        "flagged_rows": failed_rows,
        "issues_summary": issues_summary,
        "quality_score": round(100 * (len(mapped_df) - failed_rows) / max(len(mapped_df), 1), 1),
    }
    return clean_records, quality_report
