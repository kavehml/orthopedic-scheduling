import pandas as pd
import json

def main():
    xls = pd.ExcelFile("CONTRAINTS.xlsx")
    summary = {}
    for sheet in xls.sheet_names:
        df = xls.parse(sheet)
        summary[sheet] = {
            "columns": df.columns.tolist(),
            "sample_rows": df.head().to_dict(orient="records"),
            "row_count": len(df)
        }
    with open("constraints_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

if __name__ == "__main__":
    main()

