import json
from api import endpoints


class ProcessProperty:
    def __init__(
        self,
        nomor_berkas,
        tahun_berkas,
        kantor_id,
        tipe_berkas,
        sistem_koordinat,
        jumlah_persil_baru,
        desa_id,
        gambar_ukur,
    ):
        self._nomor_berkas = nomor_berkas
        self._tahun_berkas = tahun_berkas
        self._kantor_id = kantor_id
        self._tipe_berkas = tipe_berkas
        self._sistem_koordinat = sistem_koordinat
        self._jumlah_persil_baru = jumlah_persil_baru
        self._desa_id = desa_id
        self._gambar_ukur = gambar_ukur

        self._data_spasial = None

        self._load_data()

    def _load_data(self):
        response = endpoints.get_process_info(
            self._nomor_berkas,
            self._tahun_berkas,
            self._kantor_id,
            self._wilayah_id,
            self._gambar_ukur,
        )
        response_json = json.loads(response.content)
        self._data_spasial = response_json

    @property
    def nomor_berkas(self):
        return self._nomor_berkas

    @property
    def tahun_berkas(self):
        return self._tahun_berkas

    @property
    def kantor_id(self):
        return self._kantor_id

    @property
    def tipe_berkas(self):
        return self._tipe_berkas

    @property
    def sistem_koordinat(self):
        return self._sistem_koordinat

    @property
    def jumlah_persil_baru(self):
        return self._jumlah_persil_baru

    @property
    def desa_id(self):
        return self._desa_id

    @property
    def gambar_ukur(self):
        return self._gambar_ukur

    @property
    def kode_desa(self):
        if not self._data_spasial:
            self._load_data()
            return self.kode_desa()

        return self._data_spasial["infoUmum"]
