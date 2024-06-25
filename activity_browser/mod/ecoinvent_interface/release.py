from ecoinvent_interface.release import *
from ecoinvent_interface.core import *

import pyprind


class ABEcoinventRelease(EcoinventRelease):

    def _streaming_download(
            self,
            url: str,
            params: dict,
            directory: Path,
            filename: str,
            headers: Optional[dict] = {},
            zipped: Optional[bool] = False,
    ) -> None:
        """
        Reimplemented _streaming_download with Pyprind.progbar as download bar
        """
        out_filepath = directory / (filename + ".gz" if zipped else filename)
        with requests.get(
                url, stream=True, headers=headers, params=params, timeout=60
        ) as response, open(out_filepath, "wb") as out_file:
            if response.status_code != 200:
                raise requests.exceptions.HTTPError(
                    f"URL '{url}'' returns status code {response.status_code}."
                )
            download = response.raw
            chunk = 128 * 1024

            size = int(response.headers["Content-Length"])
            dl_bar = pyprind.ProgBar(size, title="Downloading from ecoinvent")

            while True:
                segment = download.read(chunk)
                if not segment:
                    break
                dl_bar.update(chunk)
                out_file.write(segment)

        message = """Downloaded file with `_streaming_download`.
    Filename: {filename}
    Directory: {self.storage.dir}
    File size (bytes): {actual}
    Class: {self.__class__.__name__}
    Instance ID: {id(self)}
    Version: {__version__}
    User: {self.username}
        """
        logger.debug(message)

        logger.info("Unzipping download")

        if zipped:
            with open(out_filepath, "rb") as source, open(
                    directory / filename, "w", encoding="utf-8"
            ) as target:
                gzip_fd = gzip.GzipFile(fileobj=source)
                target.write(gzip_fd.read().decode("utf-8-sig"))
            try:
                out_filepath.unlink()
            except PermissionError:
                # Error on Windows during testing
                message = """"Can't automatically delete {out_filepath}
    Please delete manually"""
                warnings.warn(message)

    def get_release(
        self,
        version: str,
        system_model: str,
        release_type: ReleaseType,
        extract: Optional[bool] = True,
        force_redownload: Optional[bool] = False,
        fix_version: Optional[bool] = True,
    ) -> Path:
        if not isinstance(release_type, ReleaseType):
            raise ValueError("`release_type` must be an instance of `ReleaseType`")

        abbr = SYSTEM_MODELS.get(system_model, system_model)
        filename = release_type.filename(version=version, system_model_abbr=abbr)
        available_files = self._filename_dict(version=version)

        if filename not in available_files:
            # Sometimes the filename prediction doesn't work, as not every filename
            # follows our patterns. But these exceptions are unpredictable, it's
            # just easier to find the closest match and log the correction
            # than build a catalogue of exceptions.
            possible = sorted(
                [
                    (damerau_levenshtein(filename, maybe), maybe)
                    for maybe in available_files
                ]
            )[0]
            if possible[0] <= 3:
                logger.info(
                    f"Using close match {possible[1]} for predicted filename {filename}"
                )
                filename = possible[1]
            else:
                ERROR = """"Can't find predicted filename {filename}.
    Closest match is {possible[1]}.
    Filenames for this version:""" + "\n\t".join(
                    available_files
                )
                raise ValueError(ERROR)

        cached = filename in self.storage.catalogue
        result_path = self._download_and_cache(
            filename=filename,
            uuid=available_files[filename]["uuid"],
            modified=available_files[filename]["modified"],
            expected_size=available_files[filename]["size"],
            url_namespace="r",
            extract=extract,
            force_redownload=force_redownload,
            version=version,
            system_model=system_model,
            kind="release",
        )

        SPOLD_FILES = (ReleaseType.ecospold, ReleaseType.lci, ReleaseType.lcia)
        if fix_version and release_type in SPOLD_FILES and not cached:
            major, minor = major_minor_from_string(version)
            if (result_path / "datasets").is_dir():
                logger.info("Fixing versions in unit process datasets")

                for filepath in pyprind.prog_bar(list((result_path / "datasets").iterdir()),
                                                 title="Fixing versions in unit process data"):
                    if not filepath.suffix.lower() == ".spold":
                        continue
                    fix_version_upr(
                        filepath=filepath, major_version=major, minor_version=minor
                    )
            if (result_path / "MasterData").is_dir():
                logger.info("Fixing versions in master data")
                for filepath in pyprind.prog_bar(list((result_path / "MasterData").iterdir()),
                                                 title="Fixing versions in master data"):
                    if not filepath.suffix.lower() == ".xml":
                        continue
                    fix_version_meta(
                        filepath=filepath, major_version=major, minor_version=minor
                    )

        return result_path
