
# -*- coding: utf-8 -*-
"""
aodn_hf_radar_processor.py

Structured processor for IMOS ACORN HF Radar currents on AODN S3,
modeled after a "processor" style (similar to sentinel2_processor.py).

Features:
  - Anonymous S3 browsing and file discovery (AODN public bucket)
  - Bulk download of hourly NetCDFs by month/day (preserves structure)
  - Optional per-day merge into a single NetCDF
  - Fast quiver plots for individual time steps
  - Batch PNG rendering and per-month GIF assembly
  - End-to-end helpers

Dependencies:
  pip install s3fs xarray dask imageio matplotlib cartopy cmocean
"""
from __future__ import annotations

import os
import glob
import calendar
from pathlib import Path
from typing import List, Tuple, Optional, Iterable, Dict

import numpy as np
import xarray as xr
import dask
from s3fs import S3FileSystem
import imageio.v2 as imageio
import matplotlib.pyplot as plt

# cartopy / cmocean are optional; we guard imports for headless environments
try:
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    HAS_CARTOPY = True
except Exception:
    HAS_CARTOPY = False

try:
    import cmocean
    CMO_SPEED = cmocean.cm.speed
except Exception:
    CMO_SPEED = None


class HFRadarProcessor:
    """
    Processor for AODN IMOS ACORN HF Radar gridded current maps.

    Directory layout under base_dir:
      - DATA/    (downloaded & combined NetCDFs)
      - PNG/     (rendered PNG frames)
      - GIF/     (monthly GIFs)
    """
    def __init__(self, base_dir: str = "data/aodn_hf_radar"):
        self.base_dir = Path(base_dir)
        self.data_dir = self.base_dir / "DATA"
        self.png_dir  = self.base_dir / "PNG"
        self.gif_dir  = self.base_dir / "GIF"
        for d in (self.base_dir, self.data_dir, self.png_dir, self.gif_dir):
            d.mkdir(parents=True, exist_ok=True)

        # public, anonymous S3
        self.fs = S3FileSystem(anon=True)

    # ---------------------------- S3 Discovery ----------------------------
    def ls(self, prefix: str) -> List[str]:
        """List keys under given prefix (e.g., 'imos-data/IMOS/ACORN')."""
        return self.fs.ls(prefix)

    def glob(self, pattern: str) -> List[str]:
        """Glob keys under AODN (e.g., 'imos-data/IMOS/ACORN/.../*.nc')."""
        return self.fs.glob(pattern)

    def month_keys(
        self, year: int, month: int, region: str = "NWA",
        qc_dir: str = "gridded_1h-avg-current-map_non-QC"
    ) -> List[str]:
        """
        Return all hourly NetCDF keys for a given YEAR-MONTH in a region.
        Keys look like: imos-data/IMOS/ACORN/{qc_dir}/{region}/YYYY/MM/DD/*.nc
        """
        pat = f"imos-data/IMOS/ACORN/{qc_dir}/{region}/{year:04d}/{month:02d}/*/*.nc"
        keys = self.glob(pat)
        return sorted(keys)

    # ---------------------------- Download & Merge ----------------------------
    def download_raw_month(
        self,
        year: int,
        month: int,
        region: str = "NWA",
        qc_dir: str = "gridded_1h-avg-current-map_non-QC",
        raw_root: Optional[Path] = None
    ) -> int:
        """
        Download all hourly files for the month, preserving the S3 directory structure.
        Returns number of files downloaded (excluding already-existing).
        """
        raw_root = Path(raw_root or (self.data_dir / "RAW"))
        keys = self.month_keys(year, month, region, qc_dir)
        count = 0
        for k in keys:
            rel = "/".join(k.split("/")[4:])  # drop 'imos-data/IMOS/ACORN'
            out_path = raw_root / rel
            out_path.parent.mkdir(parents=True, exist_ok=True)
            if not out_path.exists():
                self.fs.get(k, out_path.as_posix())
                count += 1
        print(f"[RAW] {year}-{month:02d} downloaded: {count}, total keys: {len(keys)}")
        return count

    def combine_day(
        self,
        year: int,
        month: int,
        day: int,
        region: str = "NWA",
        qc_dir: str = "gridded_1h-avg-current-map_non-QC",
        raw_root: Optional[Path] = None,
        out_root: Optional[Path] = None
    ) -> Optional[Path]:
        """
        Combine all hourly files of a given day into a single NetCDF, saved under out_root.
        Returns path to combined NetCDF or None if no inputs.
        """
        raw_root = Path(raw_root or (self.data_dir / "RAW"))
        out_root = Path(out_root or (self.data_dir / "DAILY"))
        pat = raw_root / region / f"{year:04d}" / f"{month:02d}" / f"{day:02d}" / "*.nc"
        files = sorted(glob.glob(pat.as_posix()))
        if not files:
            print(f"[DAILY] No local files for {year}-{month:02d}-{day:02d}")
            return None

        out_dir = out_root / region / f"{year:04d}" / f"{month:02d}"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_nc = out_dir / f"ACORN_{region}_{year}{month:02d}{day:02d}.nc"

        with dask.config.set(scheduler="threads"):
            ds = xr.open_mfdataset(files, combine="by_coords", parallel=False)

        # harmonize coordinates
        rename = {}
        if "TIME" in ds: rename["TIME"] = "time"
        if "LATITUDE" in ds: rename["LATITUDE"] = "lat"
        if "LONGITUDE" in ds: rename["LONGITUDE"] = "lon"
        if rename:
            ds = ds.rename(rename)

        with dask.config.set(scheduler="threads"):
            ds.load().to_netcdf(out_nc.as_posix(), mode="w")
        ds.close()
        print(f"[DAILY] Saved {out_nc}")
        return out_nc

    def combine_month_days(
        self,
        year: int,
        month: int,
        region: str = "NWA",
        qc_dir: str = "gridded_1h-avg-current-map_non-QC",
        raw_root: Optional[Path] = None,
        out_root: Optional[Path] = None
    ) -> List[Path]:
        """Combine all available days in a month; returns list of created files."""
        out_paths = []
        ndays = calendar.monthrange(year, month)[1]
        for d in range(1, ndays + 1):
            p = self.combine_day(year, month, d, region, qc_dir, raw_root, out_root)
            if p:
                out_paths.append(p)
        return out_paths

    # ---------------------------- Visualization ----------------------------
    @staticmethod
    def _rename_coords(ds: xr.Dataset) -> xr.Dataset:
        m = {}
        if "TIME" in ds:      m["TIME"] = "time"
        if "LATITUDE" in ds:  m["LATITUDE"] = "lat"
        if "LONGITUDE" in ds: m["LONGITUDE"] = "lon"
        return ds.rename(m) if m else ds

    def plot_quiver(
        self,
        ds: xr.Dataset,
        t_index: int = 0,
        lon_range: Optional[Tuple[float, float]] = None,
        lat_range: Optional[Tuple[float, float]] = None,
        step: int = 2,
        save_png: Optional[Path] = None
    ) -> Optional[Path]:
        """
        Quick quiver plot for a given dataset/time index.
        If save_png is provided, writes to file and returns the path.
        """
        ds = self._rename_coords(ds)
        if lon_range:
            ds = ds.sel(lon=slice(lon_range[0], lon_range[1]))
        if lat_range:
            # Note: lat slice can be south->north; xarray handles ordering
            ds = ds.sel(lat=slice(lat_range[0], lat_range[1]))

        lon_1d = ds["lon"].values[::step]
        lat_1d = ds["lat"].values[::step]
        X, Y = np.meshgrid(lon_1d, lat_1d)

        U = ds["UCUR"].isel(time=t_index).values[::step, ::step]
        V = ds["VCUR"].isel(time=t_index).values[::step, ::step]
        spd = np.hypot(U, V)

        # mask NaNs
        mask = np.isnan(spd)
        U_m = np.ma.array(U, mask=mask)
        V_m = np.ma.array(V, mask=mask)
        spd_m = np.ma.array(spd, mask=mask)

        if HAS_CARTOPY:
            fig, ax = plt.subplots(
                figsize=(7.2, 7.8),
                subplot_kw={"projection": ccrs.PlateCarree()}
            )
            if lon_range and lat_range:
                ax.set_extent([lon_range[0], lon_range[1], lat_range[0], lat_range[1]], ccrs.PlateCarree())
            ax.coastlines("10m")
            ax.add_feature(cfeature.LAND, facecolor="lightgray", edgecolor="none", alpha=0.7)
            gl = ax.gridlines(draw_labels=True, linewidth=0.5, alpha=0.5)
            gl.right_labels = False; gl.top_labels = False
            Q = ax.quiver(
                X, Y, U_m, V_m, spd_m,
                transform=ccrs.PlateCarree(),
                cmap=(CMO_SPEED or "viridis"),
                scale=5, scale_units="inches", pivot="middle", linewidths=0.2
            )
        else:
            fig, ax = plt.subplots(figsize=(7.2, 7.8))
            Q = ax.quiver(X, Y, U_m, V_m, spd_m, cmap=(CMO_SPEED or "viridis"),
                          scale=5, scale_units="inches", pivot="middle", linewidths=0.2)
            if lon_range and lat_range:
                ax.set_xlim(*lon_range); ax.set_ylim(*lat_range)
            ax.set_xlabel("lon"); ax.set_ylabel("lat")

        cb = plt.colorbar(Q, ax=ax, shrink=0.8, pad=0.02)
        cb.set_label("surface current speed (m/s)")
        ts = str(np.datetime_as_string(ds["time"].values[int(t_index)], unit="m"))
        ax.set_title(f"HF Radar Currents — {ts} UTC")
        plt.tight_layout()

        if save_png:
            save_png = Path(save_png)
            save_png.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(save_png.as_posix(), dpi=150, bbox_inches="tight")
            plt.close(fig)
            print("[PNG]", save_png)
            return save_png
        else:
            return None

    def render_month_pngs_and_gif(
        self,
        year: int,
        month: int,
        region: str = "NWA",
        raw_root: Optional[Path] = None,
        lon_range: Tuple[float, float] = (111.0, 114.0),
        lat_range: Tuple[float, float] = (-25.0, -20.0),
        step: int = 1,
        gif_duration: float = 0.4
    ) -> Optional[Path]:
        """
        For all locally downloaded hourly files in a month, render PNG frames and assemble a GIF.
        Returns GIF path if frames were produced, else None.
        """
        raw_root = Path(raw_root or (self.data_dir / "RAW"))
        out_dir = self.png_dir / f"{region}_{year}_{month:02d}"
        out_dir.mkdir(parents=True, exist_ok=True)

        frames: List[Path] = []
        ndays = calendar.monthrange(year, month)[1]
        for d in range(1, ndays + 1):
            day_glob = raw_root / region / f"{year:04d}" / f"{month:02d}" / f"{d:02d}" / "*.nc"
            day_files = sorted(glob.glob(day_glob.as_posix()))
            if not day_files:
                continue
            try:
                with dask.config.set(scheduler="threads"):
                    ds = xr.open_mfdataset(day_files, combine="by_coords", parallel=False)
                ds = self._rename_coords(ds)

                # valid time indices (avoid all-NaN frames)
                valid_idx = np.where(np.isfinite(ds["UCUR"]).any(dim=("lat", "lon")).values)[0]
                for ti in valid_idx:
                    ts = np.datetime_as_string(ds["time"].values[int(ti)], unit="m").replace(":", "")
                    png_path = out_dir / f"HFRadar_{region}_{ts}.png"
                    self.plot_quiver(
                        ds, t_index=int(ti),
                        lon_range=lon_range, lat_range=lat_range,
                        step=step, save_png=png_path
                    )
                    frames.append(png_path)
                ds.close()
            except Exception as e:
                print(f"[WARN] {year}-{month:02d}-{d:02d}: {e}")

        if not frames:
            print(f"[GIF] No frames for {year}-{month:02d}.")
            return None

        gif_path = self.gif_dir / f"HFRadar_{region}_{year}-{month:02d}.gif"
        with imageio.get_writer(gif_path.as_posix(), mode="I", duration=gif_duration, loop=0) as w:
            for p in sorted(frames):
                w.append_data(imageio.imread(p.as_posix()))
        print("[GIF]", gif_path)
        return gif_path

    # ---------------------------- End-to-end helpers ----------------------------
    def run_month_end_to_end(
        self,
        year: int,
        month: int,
        region: str = "NWA",
        qc_dir: str = "gridded_1h-avg-current-map_non-QC",
        download: bool = True,
        combine_daily: bool = False,
        make_gif: bool = True,
        lon_range: Tuple[float, float] = (111.0, 114.0),
        lat_range: Tuple[float, float] = (-25.0, -20.0),
        step: int = 1
    ) -> Dict[str, Optional[Path]]:
        """
        Full pipeline for a month:
          download -> (optional) daily combine -> render PNGs + GIF
        Returns dict with paths.
        """
        results: Dict[str, Optional[Path]] = {"gif": None}
        if download:
            self.download_raw_month(year, month, region, qc_dir)
        if combine_daily:
            self.combine_month_days(year, month, region, qc_dir)
        if make_gif:
            results["gif"] = self.render_month_pngs_and_gif(
                year, month, region, lon_range=lon_range, lat_range=lat_range, step=step
            )
        return results


# ---------------------------- Example Entrypoint ----------------------------
def example():
    """
    Example usage analogous to the original notebook choices.
    """
    p = HFRadarProcessor(base_dir="data/aodn_hf_radar")
    year, month, region = 2025, 8, "NWA"
    # 1) Download August 2025 hourly raw
    p.download_raw_month(year, month, region=region)
    # 2) Optional: merge each day
    # p.combine_month_days(year, month, region=region)
    # 3) Render PNGs + GIF in a study area
    p.render_month_pngs_and_gif(
        year, month, region=region,
        lon_range=(111.0, 114.0), lat_range=(-25.0, -20.0),
        step=1, gif_duration=0.4
    )

if __name__ == "__main__":
    # example()  # Uncomment to run the demo pipeline
    pass
