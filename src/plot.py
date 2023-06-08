import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def compute_tempDepart_min_dist_from_target(d_data: pd.DataFrame):
    m1 = d_data["T°C Départ Consigne"] > 40.0
    tmp = d_data["T°C Départ Consigne"] - d_data["T°C Départ"]
    d_data.insert(0, "T°C Départ diff", tmp)
    tmp = d_data["T°C Départ diff"][m1]
    if tmp.shape[0] < 10:
        return None
    idx = tmp.idxmin()
    return tmp.min()


def compute_average(
    d_data,
    colname: str,
    start_hour: str = "08:00:00",
    end_hour: str = "20:00:00",
    day_index: int = 0,
) -> None | float:
    day = f"{d_data.index[day_index].year}-{d_data.index[day_index].month}-{d_data.index[day_index].day}"
    start = f"{day} {start_hour}"
    end = f"{day} {end_hour}"
    tmp = d_data.loc[start:end][colname]
    return None if tmp.shape[0] == 0 else tmp.min()


def compute_ESC_indexes(d_data: pd.DataFrame):
    data = d_data["T°C ECS"].dropna()
    if data.shape[0] == 0:
        return {"ESC T min": np.nan, "ESC T max": np.nan, "ESC T mean": np.nan}
    return {"ESC T min": data.min(), "ESC T max": data.max(), "ESC T mean": data.mean()}


def consommation_pellet(d_data: pd.DataFrame) -> float:
    conso = (
        d_data["Niveau Sillo kg"].iloc[0]
        + d_data["Niveau tremis kg"].iloc[0]
        - d_data["Niveau Sillo kg"].iloc[-1]
        - d_data["Niveau tremis kg"].iloc[-1]
    )
    if conso < 0:
        conso = 0
    return conso


def fire_on_time(d_data: pd.DataFrame) -> pd.DataFrame:
    return d_data[d_data["T°C Flamme"] > 200.0].shape[0] / 60.0


def plot_data(ax: plt.Axes, d_data: pd.DataFrame, col_to_draw: str, y_label: str):
    ax.plot(d_data[col_to_draw], ".")
    # ax.set_xticks(ax.get_xticks(),rotation=45, ha='right');
    ax.set_ylabel(y_label)
    ax.legend(col_to_draw)
    # t =ax.get_xticks()
    # ax.set_xticks(np.linspace(t[0],t[-1],int((t[-1]-t[0])*12)))
    ax.tick_params(labelrotation=45)
    ax.grid(axis="x", color="0.95")
