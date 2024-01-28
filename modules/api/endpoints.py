import platform
from qgis.core import QgsExpressionContextUtils
from .base import api


ARCH = platform.processor()
QGIS_VERSION = QgsExpressionContextUtils.globalScope().variable("qgis_version")
DEFAULT_PROVIDER = "OracleMembershipProvider"
DEFAULT_APP_NAME = "KKPWeb"
DEFAULT_APP_VERSION = "4.3.0.0"


# Login Sequence
@api(endpoint="validateUser")
def login(username, password, **kwargs):
    return {
        "providerName": DEFAULT_PROVIDER,
        "applicationName": DEFAULT_APP_NAME,
        "versi": DEFAULT_APP_VERSION,
        "username": username,
        "password": password,
    }


@api(endpoint="getUserByUserName")
def get_user_by_username(username, user_is_online=True, **kwargs):
    return {
        "providerName": DEFAULT_PROVIDER,
        "applicationName": DEFAULT_APP_NAME,
        "username": username,
        "userIsOnline": user_is_online,
    }


@api(endpoint="getEntityByUserName")
def get_entity_by_username(username, **kwargs):
    return {"username": username}


@api(endpoint="getUserEntityByUserName")
def get_user_entity_by_username(
    username, kantor_id, only_valid=True, app_version="", processor_arch="", **kwargs
):
    return {
        "username": username,
        "OnlyValid": only_valid,
        "kantorid": kantor_id,
        "clientAppVersion": app_version,
        "clientProcessorArch": processor_arch,
    }


@api(endpoint="isESertipikat")
def get_is_e_sertifikat(kantor_id):
    return {"kantorId": str(kantor_id)}


@api(endpoint="getPropinsi")
def get_provinsi_by_kantor(kantor_id, tipe_kantor_id, **kwargs):
    tipe_kantor_id = str(tipe_kantor_id) if tipe_kantor_id else ""
    return {"kantorId": kantor_id, "tipeKantorId": tipe_kantor_id}


@api(endpoint="getKabupaten")
def get_kabupaten_by_kantor(kantor_id, tipe_kantor_id, propinsi_id, **kwargs):
    return {
        "kantorId": kantor_id,
        "tipeKantorId": tipe_kantor_id,
        "propinsiId": propinsi_id,
    }


@api(endpoint="getKecamatan")
def get_kecamatan_by_kantor(kantor_id, tipe_kantor_id, kabupaten_id, **kwargs):
    return {
        "kantorId": kantor_id,
        "tipeKantorId": tipe_kantor_id,
        "kabupatenId": kabupaten_id,
    }


@api(endpoint="getDesa")
def get_desa_by_kantor(kantor_id, tipe_kantor_id, kecamatan_id, **kwargs):
    return {
        "kantorId": kantor_id,
        "tipeKantorId": tipe_kantor_id,
        "kecamatanId": kecamatan_id,
    }


@api(endpoint="getProfileGeo")
def get_profile_geo(kantor_id, user_id, **kwargs):
    return {"kantorId": kantor_id, "userId": user_id}


@api(endpoint="getProgram")
def get_program_by_kantor(kantor_id, **kwargs):
    return {"kantorId": kantor_id}


@api(endpoint="getProgramInvent")
def get_program_invent_by_kantor(kantor_id, **kwargs):
    return {"kantorId": kantor_id}


@api(endpoint="getProgramParticipatoryMapping")
def get_program_participatory_mapping_by_kantor(kantor_id, **kwargs):
    return {"kantorId": kantor_id}


@api(endpoint="getNotifikasi")
def get_notifikasi_by_kantor(kantor_id, **kwargs):
    return {"kantorId": kantor_id}


# Buka Berkas Sequence
@api(endpoint="getBerkas")
def get_berkas(
    kantor_id,
    tahun_berkas=None,
    nomor_berkas="",
    tipe_kantor_id=None,
    start=0,
    limit=20,
    count=-1,
    **kwargs
):
    return {
        "nomorBerkas": nomor_berkas,
        "tahunBerkas": tahun_berkas,
        "kantorId": kantor_id,
        "tipeKantorId": tipe_kantor_id,
        "start": start,
        "limit": limit,
        "count": count,
    }


@api(endpoint="startBerkasSpasial")
def start_berkas_spasial(
    nomor_berkas, tahun_berkas, kantor_id, tipe_kantor_id, username, **kwargs
):
    return {
        "nomorBerkas": nomor_berkas,
        "tahunBerkas": tahun_berkas,
        "kantorId": kantor_id,
        "tipeKantorId": tipe_kantor_id,
        "userName": username,
        "versi": DEFAULT_APP_VERSION,
    }


@api(endpoint="getSpatialDocumentSdo")
def get_spatial_document_sdo(gugus_ids, include_riwayat=False, **kwargs):
    return {"gugusId": gugus_ids, "getRiwayat": include_riwayat}


@api(endpoint="getBlankoByBerkasId")
def get_blanko_by_berkas_id(berkas_id, status_blanko="P", **kwargs):
    return {"berkasId": berkas_id, "statusBlanko": status_blanko}


# Simpan Berkas Sequence
@api(endpoint="getWilayahPrior")
def get_wilayah_prior(wilayah_id, **kwargs):
    return {"wilayahId": wilayah_id}


@api(endpoint="getParcels")
def get_parcels(persil_ids, **kwargs):
    return persil_ids


@api(endpoint="getApartments")
def get_apartments(apartment_ids, **kwargs):
    return apartment_ids


@api(endpoint="submitSdo")
def submit_sdo(
    nomor_berkas,
    tahun_berkas,
    kantor_id,
    tipe_kantor_id,
    wilayah_id,
    petugas_id,
    user_id,
    gugus_ids,
    gu_id,
    sistem_koordinat="TM3",
    keterangan="",
    reset302=False,
    sdo_to_submit={},
    **kwargs
):
    return {
        "nomorBerkas": nomor_berkas,
        "tahunBerkas": tahun_berkas,
        "kantorId": kantor_id,
        "tipeKantorId": tipe_kantor_id,
        "wilayahId": wilayah_id,
        "sistemKoordinat": sistem_koordinat,
        "keterangan": keterangan,
        "namapetugas": petugas_id,
        "gugusId": gugus_ids,
        "guId": gu_id,
        "reset302": reset302,
        "userid": user_id,
        "sts": sdo_to_submit,
    }


@api(endpoint="getParcelNotLinkedTo302")
def get_parcel_not_linked_to_302(berkas_id, pengukuran_ulang=True, **kwargs):
    return {"berkasId": berkas_id, "pengukuranUlang": pengukuran_ulang}


@api(endpoint="get302NotLinkedToParcel")
def get_302_not_linked_to_parcel(berkas_id, **kwargs):
    return {"berkasId": berkas_id}


@api(endpoint="getParcelLinkedTo302")
def get_parcel_linked_to_302(berkas_id, **kwargs):
    return {"berkasId": berkas_id}


@api(endpoint="autoLinkParcelToDI302")
def autolink_parcel_to_302(berkas_id, **kwargs):
    return {"berkasId": berkas_id}


@api(endpoint="checkPetaBidang")
def check_peta_bidang(berkas_id, **kwargs):
    return {"berkasId": berkas_id}


@api(endpoint="createPetaBidang")
def create_peta_bidang(berkas_id, mode, kantor_id, wilayah_id, petugas_id, **kwargs):
    return {
        "berkasId": berkas_id,
        "mode": mode,
        "kantorId": kantor_id,
        "wilayahId": wilayah_id,
        "petugas": petugas_id,
    }


@api(endpoint="stopBerkas")
def stop_berkas(nomor_berkas, tahun_berkas, kantor_id, **kwargs):
    return {
        "nomorBerkas": nomor_berkas,
        "tahunBerkas": tahun_berkas,
        "kantorId": kantor_id,
    }


# Utilities
@api(endpoint="GetZonaTm3ByBerkas")
def get_zona_tm3_by_berkas(nomor_berkas, tahun_berkas, kantor_id, **kwargs):
    return {
        "nomorBerkas": nomor_berkas,
        "tahunBerkas": tahun_berkas,
        "kantorId": kantor_id,
    }


# Wilayah
@api(endpoint="unduhWilayahSdo")
def get_wilayah_sdo(wilayah_id, tipe_wilayah, srs, **kwargs):
    return {"wilayahId": wilayah_id, "tipeWilayah": tipe_wilayah, "srsName": srs}


@api(endpoint="gantiDesa")
def ganti_desa(
    nomor_berkas,
    tahun_berkas,
    kantor_id,
    tipe_kantor_id,
    wilayah_baru,
    object_name,
    object_lama,
    user_id,
    **kwargs
):
    return {
        "nomorBerkas": nomor_berkas,
        "tahunBerkas": tahun_berkas,
        "kantorId": kantor_id,
        "tipeKantorId": tipe_kantor_id,
        "wilayahBaru": wilayah_baru,
        "objectName": object_name,
        "objectLama": object_lama,
        "userId": user_id,
    }


@api(endpoint="getProcessInfo")
def get_process_info(
    nomor_berkas, tahun_berkas, kantor_id, wilayah_id, gu_id, **kwargs
):
    return {
        "nomorBerkas": nomor_berkas,
        "tahunBerkas": tahun_berkas,
        "kantorId": kantor_id,
        "wilayahId": wilayah_id,
        "guId": gu_id,
    }


@api(endpoint="getLandUseData")
def get_landuse_data(**kwargs):
    return None


@api(endpoint="getAlatUkur")
def get_alat_ukur(**kwargs):
    return None


@api(endpoint="getMetodeUkur")
def get_metode_ukur(**kwargs):
    return None


@api(endpoint="getParcelInfo")
def get_parcel_info(persil_id, **kwargs):
    return {"persilId": persil_id}


@api(endpoint="updatePersil")
def update_persil(dataset):
    return {"dSet": dataset}


@api(endpoint="getPBTForApbn")
def get_pbt_for_apbn(
    nomor_pbt="",
    tahun_pbt="",
    kantor_id="",
    proyek="",
    tipe_pbt="",
    start=0,
    limit=20,
    count=-1,
    **kwargs
):
    return {
        "nomorPBT": nomor_pbt,
        "tahunPBT": tahun_pbt,
        "kantorId": kantor_id,
        "proyek": proyek,
        "tipePBT": tipe_pbt,
        "start": start,
        "limit": limit,
        "count": count,
    }


@api(endpoint="createNewPetaNominatif")
def create_new_peta_normatif(
    petugas, kendali_id, berkas_id, wilayah_id, kantor_id, pegawai_id, **kwargs
):
    return {
        "petugas": petugas,
        "kendaliId": kendali_id,
        "berkasId": berkas_id,
        "wilayahId": wilayah_id,
        "kantorId": kantor_id,
        "pegawaiId": pegawai_id,
    }


@api(endpoint="createNewPBTForApbn")
def create_new_pbt_for_apbn(
    petugas, program_id, wilayah_id, kantor_id, tipe_pbt, **kwargs
):
    return {
        "petugas": petugas,
        "programId": program_id,
        "wilayahId": wilayah_id,
        "kantorId": kantor_id,
        "tipePBT": tipe_pbt,
    }


@api(endpoint="startEditPBTForApbn")
def start_edit_pbt_for_apbn(dokumen_pengukuran_id, username, **kwargs):
    return {"dokumenPengukuranId": dokumen_pengukuran_id, "userName": username}


@api(endpoint="getRincikanbyPbt")
def get_rincikan_by_pbt(peta_bidang_id, **kwargs):
    return {"petabidangid": peta_bidang_id}


@api(endpoint="getLimitPersilPbt")
def get_limit_persil_pbt(peta_bidang_id="", kantor_id="", **kwargs):
    return {"petabidangId": peta_bidang_id, "kantorId": kantor_id}


@api(endpoint="submitForPtslKtRedis")
def submit_for_ptsl_kt_redis(
    dokumen_pengukuran_id="",
    program_id="",
    kantor_id="",
    wilayah_id="",
    sistem_koordinat="",
    keterangan="",
    petugas="",
    sts={},
    gugus_id="",
    gu_id="",
    user_id="",
    jumlah_persil="",
    **kwargs
):
    return {
        "dokumenPengukuranId": dokumen_pengukuran_id,
        "programId": program_id,
        "kantorId": kantor_id,
        "wilayahId": wilayah_id,
        "sistemKoordinat": sistem_koordinat,
        "keterangan": keterangan,
        "petugas": petugas,
        "sts": sts,
        "gugusId": gugus_id,
        "guId": gu_id,
        "userId": user_id,
        "jumlahPersil": jumlah_persil,
    }


@api(endpoint="stopPBT")
def stop_pbt(dokumen_pengukuran_id, **kwargs):
    return {"dokumenPengukuranId": dokumen_pengukuran_id}


@api(endpoint="uploadDxfPbtSkb")
def upload_dxf_pbt_skb(
    kantor_id="", mitra_kerja_id="", dok_ukur_id="", file="", **kwargs
):
    return {
        "kantorId": kantor_id,
        "mitrakerjaId": mitra_kerja_id,
        "dokukurId": dok_ukur_id,
        "theFile": file,
    }


@api(endpoint="cekMapping")
def cek_mapping(persil_ids, **kwargs):
    return persil_ids


@api(endpoint="finnishPBT")
def finish_pbt(dokumen_pengukuran_id, **kwargs):
    return {"dokumenPengukuranId": dokumen_pengukuran_id}
