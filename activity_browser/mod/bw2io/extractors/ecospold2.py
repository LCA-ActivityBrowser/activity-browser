from bw2io.extractors.ecospold2 import *


class ABEcospold2DataExtractor(Ecospold2DataExtractor):

    def __init__(self, progress_slot):
        self.progress_slot = progress_slot

    def extract(self, dirpath, db_name, use_mp=True):
        assert os.path.exists(dirpath)
        if os.path.isdir(dirpath):
            filelist = [
                filename
                for filename in os.listdir(dirpath)
                if os.path.isfile(os.path.join(dirpath, filename))
                and filename.split(".")[-1].lower() == "spold"
            ]
        elif os.path.isfile(dirpath):
            filelist = [dirpath]
        else:
            raise OSError("Can't understand path {}".format(dirpath))

        if sys.version_info < (3, 0):
            use_mp = False

        if use_mp:
            with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
                print("Extracting XML data from {} datasets".format(len(filelist)))
                results = [
                    pool.apply_async(
                        Ecospold2DataExtractor.extract_activity,
                        args=(dirpath, x, db_name),
                    )
                    for x in filelist
                ]
                data = [p.get() for p in results]
        else:
            pbar = pyprind.ProgBar(
                len(filelist), title="Extracting ecospold2 files:", monitor=True
            )

            data = []
            for index, filename in enumerate(filelist):
                self.progress_slot(int(index/len(filelist) * 100), "Extracting ecospold2 data")
                data.append(self.extract_activity(dirpath, filename, db_name))
                pbar.update(item_id=filename[:15])

            print(pbar)

        if sys.version_info < (3, 0):
            print("Converting to unicode")
            return recursive_str_to_unicode(data)
        else:
            return data