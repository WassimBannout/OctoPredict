from pydantic import BaseModel


class TeamBase(BaseModel):
    external_id: int
    name: str
    short_name: str
    tla: str
    crest_url: str | None
    competition_code: str


class TeamResponse(TeamBase):
    id: int
    current_elo: float | None = None

    model_config = {"from_attributes": True}


class TeamDetail(TeamResponse):
    elo_history: list[dict] = []
    home_record: dict = {}
    away_record: dict = {}
    last_5_matches: list[dict] = []
