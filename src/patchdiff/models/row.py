from datetime import date
from math import isnan
from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator

BEGINNING_OF_TIME = date(1900, 1, 1)
END_OF_TIME = date(9999, 12, 31)

class PatchRow(BaseModel):
    model_config = ConfigDict(extra='allow', populate_by_name=True)

    begin_date: date = Field(default=BEGINNING_OF_TIME, alias="BeginDate")
    end_date: date = Field(default=END_OF_TIME, alias="EndDate")

    @field_validator("begin_date", "end_date", mode="before")
    @classmethod
    def normalize_date(cls, value, info):
        if value is None or (isinstance(value, float) and isnan(value)):
            return (
                BEGINNING_OF_TIME
                if info.field_name == "begin_date"
                else END_OF_TIME
            )

        if isinstance(value, (int, float)):
            value = str(int(value))

        if isinstance(value, str):
            value = value.strip()

            if not value:
                return (
                    BEGINNING_OF_TIME
                    if info.field_name == "begin_date"
                    else END_OF_TIME
                )

            if len(value) == 8 and value.isdigit():
                return date(
                    int(value[:4]),
                    int(value[4:6]),
                    int(value[6:8]),
                )

        return value

    @model_validator(mode="after")
    def validate_dates(self):
        if self.begin_date > self.end_date:
            raise ValueError(
                "begin_date must be before or equal to end_date"
            )

        if not self.model_extra:
            raise ValueError(
                "Row must contain at least one column besides "
                "begin_date and end_date"
            )

        return self