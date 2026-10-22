from pydantic import BaseModel, ConfigDict, Field


class ORMReadSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PaginatedQuery(BaseModel):
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=100, ge=1, le=500)
