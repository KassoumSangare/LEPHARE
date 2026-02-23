from typing import Any, Callable, List

import pandas as pd
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import InMemoryUploadedFile


class ExcelFileValidator:
    def __init__(self, max_file_size: int = 5 * 1024 * 1024):
        self.max_file_size = max_file_size
        self.validators: List[Callable[[Any], None]] = [
            self.validate_file_size,
            self.validate_excel_format,
        ]

    def validate(self, file: InMemoryUploadedFile) -> None:
        for validator in self.validators:
            validator(file)

    def validate_file_size(self, file: InMemoryUploadedFile) -> None:
        if file.size > self.max_file_size:
            raise ValidationError(
                f"La taille du fichier excède {self.max_file_size / (1024 * 1024):.2f} Mo."
            )

    def validate_excel_format(self, file: InMemoryUploadedFile) -> None:
        try:
            pd.read_excel(file)
        except Exception as e:
            raise ValidationError(f"Fichier Excel invalide: {str(e)}")
        finally:
            file.seek(0)  # Reset file pointer


class ExcelColumnValidator:
    def __init__(self, expected_columns: List[str]):
        self.expected_columns = expected_columns

    def validate(self, file: InMemoryUploadedFile) -> None:
        df = pd.read_excel(file)

        actual_columns = df.columns.tolist()

        if actual_columns != self.expected_columns:
            raise ValidationError("Noms de colonne inconnus!")


class ExcelFileHandler:
    def __init__(
        self,
        file_validator: ExcelFileValidator,
        column_validator: ExcelColumnValidator,
    ):
        self.file_validator = file_validator
        self.column_validator = column_validator

    def handle(self, file: InMemoryUploadedFile) -> dict:
        result = {
            "file_name": file.name,
            "file_size": file.size,
            "is_valid_excel": True,
            "columns_match": True,
            "errors": [],
        }

        try:
            self.file_validator.validate(file)
        except ValidationError as e:
            result["is_valid_excel"] = False
            result["errors"].append(str(e))

        if result["is_valid_excel"]:
            try:
                self.column_validator.validate(file)
            except ValidationError as e:
                result["columns_match"] = False
                result["errors"].append(str(e))

        return result
