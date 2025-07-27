from csv_import import process_csv_file
from app import app, db
from models import CSVImport

with app.app_context():
    file_path = r"C:\Users\Sadman\Desktop\VantaTrack\uploads\Campaign report.csv"

    new_import = CSVImport(
        filename="Campaign report.csv",
        file_path=file_path,
        status="Queued",
        rows_processed=0,
        rows_failed=0
    )
    db.session.add(new_import)
    db.session.commit()

    import_id = new_import.id
    result = process_csv_file(file_path)
    print(result)
    result = process_csv_file(file_path)

    if result[0]:  # Check if True
       print(result[1])  # Message like 'Processed 0 rows, 0 failed'
    else:
       print("Import failed:", result[1])
