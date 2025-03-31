import dash
from dash import dcc, html, Output, Input
import pandas as pd
import plotly.express as px
import os

# Загружаем все файлы, оканчивающиеся на '38.csv'
files = [f for f in os.listdir() if f.endswith("38.csv")]
data = {}

for file in files:
    company_name = file.replace("38.csv", "")
    df = pd.read_csv(file, parse_dates=["datetime"])
    data[company_name] = df

# Загружаем файлы со статистикой
stat_files = [f for f in os.listdir() if f.endswith("_1_min.csv")]
stats_data = {}

for file in stat_files:
    company_name = file.replace("_stats.csv", "")
    # df = pd.read_csv(file, parse_dates=["utc"])
    stats_data[company_name] = pd.read_csv(file, dtype={"utc": "object"})  # Читаем как строку
    stats_data[company_name]["utc"] = pd.to_datetime(
        stats_data[company_name]["utc"], 
        format="mixed",  # Формат ваших данных (пример: 2018-03-07T18:34:00.000000)
        utc=False
    )

# Создаем Dash-приложение
app = dash.Dash(__name__, external_stylesheets=['https://codepen.io/chriddyp/pen/bWLwgP.css'])

all_dates = pd.concat([df["datetime"] for df in data.values()])
min_date, max_date = all_dates.min(), all_dates.max()

# Функция для генерации меток слайдера
def generate_marks(start, end):
    dates = pd.date_range(start=start, end=end, freq='15D')
    marks = {int(date.timestamp()): date.strftime('%Y-%m-%d') for date in dates}
    return marks

app.layout = html.Div([
    # Секция бюджета
    html.Div([
        html.H3("Торги акцией по стратегии long-short с обновлением каждый месяц (выбор 2 компаний)", style={'marginTop': '20px'}),
        dcc.Checklist(
            id='company-selector',
            options=[{'label': name, 'value': name} for name in data.keys()],
            value=list(data.keys())[:2],  # Выбираем первые 2 компании по умолчанию
            inline=True
        ),
        dcc.RangeSlider(
            id='date-slider-budget',
            min=min_date.timestamp(),
            max=max_date.timestamp(),
            value=[min_date.timestamp(), max_date.timestamp()],
            marks=generate_marks(min_date, max_date),
            step=1296000
        ),
        dcc.Graph(
            id='budget-graph',
            config={
                'modeBarButtonsToAdd': ['drawline', 'drawopenpath', 'drawrect', 'eraseshape']
            })
    ], style={'marginBottom': '50px', 'border': '1px solid #ddd', 'padding': '20px'}),

    # Секция стратегий
    html.Div([
        html.H3("Результаты по отдельным действиям модели OMG", style={'marginTop': '20px'}),
        dcc.Dropdown(
            id='single-company-selector',
            options=[{'label': name, 'value': name} for name in data.keys()],
            value=list(data.keys())[0],
            clearable=False
        ),
        dcc.Checklist(
            id='strategy-selector',
            options=[],
            value=[],
            inline=True
        ),
        dcc.RangeSlider(
            id='date-slider-strategy',
            min=min_date.timestamp(),
            max=max_date.timestamp(),
            value=[min_date.timestamp(), max_date.timestamp()],
            marks=generate_marks(min_date, max_date),
            step=1296000
        ),
        dcc.Graph(
            id='strategy-graph',
            config={
                'modeBarButtonsToAdd': ['drawline', 'drawopenpath', 'drawrect', 'eraseshape']
            })
    ], style={'marginBottom': '50px', 'border': '1px solid #ddd', 'padding': '20px'}),

    # Секция статистики
    html.Div([
        html.H3("Сравнение динамики бюджета с динамикой цены закрытия/объема", style={'marginTop': '20px'}),
        dcc.Dropdown(
            id='stats-company-selector',
            options=[{'label': name, 'value': name} for name in stats_data.keys()],
            value=list(stats_data.keys())[0],
            clearable=False
        ),
        dcc.Checklist(
            id='stats-metric-selector',
            options=[
                {'label': 'Budget', 'value': 'budget'},
                {'label': 'Close', 'value': 'close'},
                {'label': 'Volume', 'value': 'volume'}
            ],
            value=['budget', 'close'],
            inline=True
        ),
        dcc.RangeSlider(
            id='date-slider-stats',
            min=min_date.timestamp(),
            max=max_date.timestamp(),
            value=[min_date.timestamp(), max_date.timestamp()],
            marks=generate_marks(min_date, max_date),
            step=1296000
        ),
        dcc.Graph(
            id='stats-graph',
            config={
                'modeBarButtonsToAdd': ['drawline', 'drawopenpath', 'drawrect', 'eraseshape']
            })
    ], style={'marginBottom': '50px', 'border': '1px solid #ddd', 'padding': '20px'})
], style={'fontFamily': 'Arial', 'maxWidth': '1200px', 'margin': '0 auto'})

# Новый callback для ограничения выбора компаний
@app.callback(
    Output('company-selector', 'value'),
    Input('company-selector', 'value')
)
def update_selected_companies(selected):
    if len(selected) > 2:
        # Оставляем только последние 2 выбранные компании
        return selected[-2:]
    return selected

@app.callback(
    Output('budget-graph', 'figure'),
    Input('company-selector', 'value'),
    Input('date-slider-budget', 'value')
)
def update_budget_graph(selected_companies, date_range):
    start_date = pd.to_datetime(date_range[0], unit='s')
    end_date = pd.to_datetime(date_range[1], unit='s')
    
    filtered_data = []
    for company in selected_companies:
        df = data[company]
        df_filtered = df[(df["datetime"] >= start_date) & (df["datetime"] <= end_date)]
        df_filtered["company"] = company
        filtered_data.append(df_filtered)
    
    if not filtered_data:
        return px.line(title="Нет данных для отображения")
    
    df_final = pd.concat(filtered_data)
    fig = px.line(df_final, x="datetime", y="budget", color="company", title="Бюджет по времени")
    return fig

@app.callback(
    Output('strategy-selector', 'options'),
    Input('single-company-selector', 'value')
)
def update_strategy_options(selected_company):
    strategies = data[selected_company]['strategy'].unique()
    return [{'label': strat, 'value': strat} for strat in strategies]

@app.callback(
    Output('strategy-graph', 'figure'),
    Input('single-company-selector', 'value'),
    Input('strategy-selector', 'value'),
    Input('date-slider-strategy', 'value')
)
def update_strategy_graph(selected_company, selected_strategies, date_range):
    start_date = pd.to_datetime(date_range[0], unit='s')
    end_date = pd.to_datetime(date_range[1], unit='s')
    
    df = data[selected_company]
    df_filtered = df[(df["datetime"] >= start_date) & 
                    (df["datetime"] <= end_date) & 
                    (df["strategy"].isin(selected_strategies))]
    
    if df_filtered.empty:
        return px.scatter(title="Нет данных для отображения")
    
    # Создаем текстовые метки для цветов
    color_mapping = {
        'red': 'Бюджет упал',
        'green': 'Бюджет вырос',
        'gray': 'Без изменений'
    }
    df_filtered['trend'] = df_filtered['color'].map(color_mapping)
    
    fig = px.scatter(
        df_filtered,
        x="datetime",
        y="budget",
        color="trend",
        title=f"Бюджет по стратегиям для {selected_company}",
        color_discrete_map={
            'Бюджет упал': 'red',
            'Бюджет вырос': 'green',
            'Без изменений': 'gray'
        },
        category_orders={"trend": ["Бюджет вырос", "Без изменений", "Бюджет упал"]}
    )
    
    # Настраиваем легенду
    fig.update_layout(
        legend_title_text='Тенденция',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.3,
            xanchor="center",
            x=0.5
        )
    )
    
    return fig

@app.callback(
    Output('stats-graph', 'figure'),
    Input('stats-company-selector', 'value'),
    Input('stats-metric-selector', 'value'),
    Input('date-slider-stats', 'value')
)
def update_stats_graph(selected_company, metrics, date_range):
    start_date = pd.to_datetime(date_range[0], unit='s')  # Убираем часовой пояс
    end_date = pd.to_datetime(date_range[1], unit='s')
    
    # Объединяем данные из двух источников
    df_stats = stats_data[selected_company]
    df_budget = data[selected_company[:-10]]
    
    # Фильтруем по дате
    df_stats = df_stats[(df_stats["utc"] >= start_date) & (df_stats["utc"] <= end_date)]
    df_budget = df_budget[(df_budget["datetime"] >= start_date) & (df_budget["datetime"] <= end_date)]
    
    # Объединяем по дате
    merged_df = pd.merge(
        df_budget[['datetime', 'budget']],
        df_stats[['utc', 'close', 'volume']],
        left_on='datetime',
        right_on='utc',
        how='inner'
    )
    
    if merged_df.empty:
        return px.line(title="Нет данных для отображения")
    
    # Создаем фигуру с вторичной осью
    fig = px.line(merged_df, x='datetime', y=metrics[0])
    
    # Добавляем вторую метрику на вторичную ось
    if len(metrics) > 1:
        fig.add_scatter(
            x=merged_df['datetime'],
            y=merged_df[metrics[1]],
            name=metrics[1],
            yaxis='y2'
        )
        
        # Настраиваем оси
        fig.update_layout(
            yaxis2=dict(
                title=metrics[1],
                overlaying='y',
                side='right'
            )
        )
    
    fig.update_layout(title=f"{', '.join(metrics)} для {selected_company}")
    return fig


if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=80) # gell
    # app.run_server(debug=True)
