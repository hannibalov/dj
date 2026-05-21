from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.setting import Setting
from app.schemas.settings import SettingsResponse, SettingsUpdate


class SettingsService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def _defaults(self) -> SettingsResponse:
        env = get_settings()
        return SettingsResponse(
            watch_folder=str(env.watch_folder),
            incoming_folder=str(env.incoming_folder),
            processing_folder=str(env.processing_folder),
            ready_folder=str(env.ready_folder),
            review_folder=str(env.review_folder),
            duplicates_folder=str(env.duplicates_folder),
            archive_folder=str(env.archive_folder),
            failed_folder=str(env.failed_folder),
            logs_folder=str(env.logs_folder),
            rekordbox_export_folder=str(env.rekordbox_export_folder),
            stability_poll_seconds=env.stability_poll_seconds,
            stability_required_seconds=env.stability_required_seconds,
            tag_confidence_threshold=env.tag_confidence_threshold,
            naming_template=env.naming_template,
            review_lufs_threshold=env.review_lufs_threshold,
            review_true_peak_db=env.review_true_peak_db,
            review_min_mp3_bitrate_kbps=env.review_min_mp3_bitrate_kbps,
            review_min_lossless_bit_depth=env.review_min_lossless_bit_depth,
            review_min_lossless_sample_rate_hz=env.review_min_lossless_sample_rate_hz,
        )

    def _load_overrides(self) -> dict[str, str]:
        rows = self._db.query(Setting).all()
        return {row.key: row.value for row in rows}

    def get_all(self) -> SettingsResponse:
        data = self._defaults().model_dump()
        data.update(self._load_overrides())
        return SettingsResponse.model_validate(data)

    def update(self, payload: SettingsUpdate) -> SettingsResponse:
        if payload.folders:
            for key, value in payload.folders.model_dump().items():
                self._upsert(key, value)
        if payload.stability_poll_seconds is not None:
            self._upsert("stability_poll_seconds", str(payload.stability_poll_seconds))
        if payload.stability_required_seconds is not None:
            self._upsert("stability_required_seconds", str(payload.stability_required_seconds))
        if payload.tag_confidence_threshold is not None:
            self._upsert("tag_confidence_threshold", str(payload.tag_confidence_threshold))
        if payload.naming_template is not None:
            self._upsert("naming_template", payload.naming_template)
        if payload.review_lufs_threshold is not None:
            self._upsert("review_lufs_threshold", str(payload.review_lufs_threshold))
        if payload.review_true_peak_db is not None:
            self._upsert("review_true_peak_db", str(payload.review_true_peak_db))
        if payload.review_min_mp3_bitrate_kbps is not None:
            self._upsert(
                "review_min_mp3_bitrate_kbps",
                str(payload.review_min_mp3_bitrate_kbps),
            )
        if payload.review_min_lossless_bit_depth is not None:
            self._upsert(
                "review_min_lossless_bit_depth",
                str(payload.review_min_lossless_bit_depth),
            )
        if payload.review_min_lossless_sample_rate_hz is not None:
            self._upsert(
                "review_min_lossless_sample_rate_hz",
                str(payload.review_min_lossless_sample_rate_hz),
            )
        self._db.commit()
        return self.get_all()

    def _upsert(self, key: str, value: str) -> None:
        row = self._db.query(Setting).filter(Setting.key == key).one_or_none()
        if row:
            row.value = value
        else:
            self._db.add(Setting(key=key, value=value))
