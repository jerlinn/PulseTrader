import plotly.graph_objs as go
from plotly.subplots import make_subplots
from datetime import datetime
from decimal import Decimal
import pandas as pd
import os

def create_stock_chart(df, stock_name, divergences, today):
    """创建股票图表并保存"""
    output_directory = "figures"
    os.makedirs(output_directory, exist_ok=True)
    
    # 使用 Pandas 的 notnull() 方法来过滤非空日期数据
    trading_df = df[df['日期'].notnull()]
    
    # 创建包含三个子图的图表：蜡烛图、交易量柱状图、RSI指标
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05, 
                        row_heights=[0.6, 0.2, 0.2],
                        subplot_titles=(' ', '', ''))

    # 添加股票的蜡烛图, legendgroup 修正图例顺序
    fig.add_trace(go.Candlestick(x=trading_df['日期'], increasing_line_color='red', decreasing_line_color='green',
                                 open=trading_df['开盘'], high=trading_df['最高'], low=trading_df['最低'], close=trading_df['收盘'],
                                 name='日 K', legendgroup='1', legendrank=1), row=1, col=1)

    # 计算每日涨跌幅
    trading_df = trading_df.copy()  # 避免 SettingWithCopyWarning
    trading_df['Change'] = trading_df['收盘'] - trading_df['开盘']
    trading_df['Color'] = trading_df['Change'].apply(lambda x: 'red' if x > 0 else 'green')

    # 添加交易量柱状图，并根据涨跌情况设置颜色
    fig.add_trace(go.Bar(x=trading_df['日期'], y=trading_df['成交量'], marker_color=trading_df['Color'], opacity=0.8, name='交易量'), row=2, col=1)

    # 添加超级趋势上轨线和下轨线
    fig.add_trace(go.Scatter(x=df['日期'], y=df['upper_band'], mode='lines', name='上轨', line=dict(color='green', shape='spline', dash='dot')), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['日期'], y=df['lower_band'], mode='lines', name='下轨', line=dict(color='orangered', shape='spline', dash='dot')), row=1, col=1)

    # 添加MA10线
    _add_ma10_line(fig, df)
    
    # 添加趋势填充
    _add_trend_filling(fig, df)
    
    # 添加信号标记
    _add_signal_markers(fig, df)

    # 添加 RSI 指标线到第三个子图
    fig.add_trace(go.Scatter(
        x=df['日期'], y=df['rsi'],
        mode='lines',
        line=dict(color='#FF8C1E', width=2),
        name='RSI'
    ), row=3, col=1)

    # RSI 关键区域参考线-严格
    fig.add_hline(y=80, line_dash="dot", line_color="red", opacity=0.5, row=3, col=1)     # 超买线
    fig.add_hline(y=20, line_dash="dot", line_color="green", opacity=0.5, row=3, col=1)   # 超卖线

    # 添加RSI背离标记
    if not divergences.empty:
        _add_divergence_markers(fig, df, divergences)
        
    # 更新图表布局
    _update_layout(fig, df, stock_name)

    # 保存图表
    fig_name = f'{output_directory}/{stock_name}_TrendSight_{today}.png'
    fig.write_image(fig_name, scale=2)
    
    print(f"图表已保存至: {fig_name}")
    return fig

def _add_ma10_line(fig, df):
    """添加MA10移动平均线"""
    # 计算10日移动平均线
    ma_10 = df['收盘'].rolling(window=10).mean()

    # 初始化 MA10 颜色列表
    ma10_colors = []

    # 遍历数据，根据趋势设置 MA10 颜色
    for trend in df['trend']:
        if trend == -1:
            ma10_colors.append('green')  # 下跌趋势用绿色
        else:
            ma10_colors.append('red')  # 上涨趋势用红色

    # 添加 MA10 线，颜色随趋势变化
    for idx in range(len(df) - 1):
        fig.add_trace(go.Scatter(
            x=[df['日期'].iloc[idx], df['日期'].iloc[idx + 1]],
            y=[ma_10.iloc[idx], ma_10.iloc[idx + 1]],
            mode='lines', line=dict(color=ma10_colors[idx], width=1, shape='spline'),
            showlegend=False
        ), row=1, col=1)

        # 在线段的两端添加圆形标记
        fig.add_trace(go.Scatter(
            x=[df['日期'].iloc[idx], df['日期'].iloc[idx + 1]],
            y=[ma_10.iloc[idx], ma_10.iloc[idx + 1]],
            mode='markers', marker=dict(color=ma10_colors[idx], size=1),
            showlegend=False
        ), row=1, col=1)

def _add_trend_filling(fig, df):
    """添加趋势填充区域"""
    # 检测趋势变化
    df['Trend_Change'] = df['trend'].diff()

    # 识别连续的趋势区间
    trend_sections = df['Trend_Change'].abs().cumsum().fillna(0)

    # 对每个连续的趋势区间应用填充
    for section in trend_sections.unique():
        section_df = df[trend_sections == section]
        
        # 上涨趋势填充
        if not section_df.empty and section_df['trend'].iloc[0] == 1:
            fig.add_trace(go.Scatter(
                x=section_df['日期'], y=section_df['收盘'],
                mode='lines', line=dict(width=0), showlegend=False
            ), row=1, col=1)
            fig.add_trace(go.Scatter(
                x=section_df['日期'], y=section_df['lower_band'],
                mode='lines', fill='tonexty', line=dict(width=0), fillcolor='rgba(255,0,0,0.1)', showlegend=False
            ), row=1, col=1)
        
        # 下跌趋势填充
        elif not section_df.empty and section_df['trend'].iloc[0] == -1:
            fig.add_trace(go.Scatter(
                x=section_df['日期'], y=section_df['收盘'],
                mode='lines', line=dict(width=0), showlegend=False
            ), row=1, col=1)
            fig.add_trace(go.Scatter(
                x=section_df['日期'], y=section_df['upper_band'],
                mode='lines', fill='tonexty', line=dict(width=0), fillcolor='rgba(0,255,0,0.2)', showlegend=False
            ), row=1, col=1)

def _add_signal_markers(fig, df):
    """添加买卖信号标记"""
    # 计算趋势变化点
    df['trend_shifted'] = df['trend'].shift(1)
    b_positions = df[(df['trend'] == 1) & (df['trend_shifted'] != 1)].index
    s_positions = df[(df['trend'] == -1) & (df['trend_shifted'] != -1)].index
    
    # 在 B 信号的位置上添加标记，使用下轨值（lower_band）作为位置
    fig.add_trace(go.Scatter(
        x=[df.loc[pos, '日期'] for pos in b_positions], 
        y=[df.loc[pos, 'lower_band'] * Decimal('0.995') for pos in b_positions],
        mode='markers', name='UP', 
        marker=dict(symbol='arrow', color='orangered', size=10)
    ), row=1, col=1)

    # 在 S 信号的位置上添加标记，使用上轨值（upper_band）作为位置
    fig.add_trace(go.Scatter(
        x=[df.loc[pos, '日期'] for pos in s_positions], 
        y=[df.loc[pos, 'upper_band'] * Decimal('1.005') for pos in s_positions],
        mode='markers', name='DOWN', 
        marker=dict(symbol='arrow', angle=180, color='green', size=10)
    ), row=1, col=1)

def _add_divergence_markers(fig, df, divergences):
    """添加RSI背离标记"""
    for _, div in divergences.iterrows():
        div_date = div['date']
        if div_date in df['日期'].values:
            color = 'green' if div['type'] == 'bearish' else 'red'
            symbol = 'arrow'
            angle = 180 if div['type'] == 'bearish' else 0
            
            # 在第一个价格子图添加半透明白色辅助线
            fig.add_vline(
                x=div_date,
                line_dash="solid",
                line_color="rgba(255, 255, 255, 0.7)",
                line_width=1,
                row=1, col=1
            )
            
            # 在RSI图上标记背离
            date_mask = df['日期'] == div_date
            if date_mask.any():
                rsi_value = df.loc[date_mask, 'rsi'].iloc[0]
                fig.add_trace(go.Scatter(
                        x=[div_date],
                        y=[rsi_value],
                        mode='markers',
                        marker=dict(
                            size=12,
                            color=color,
                            symbol=symbol,
                            angle=angle,
                        ),
                        showlegend=False
                    ), row=3, col=1)

def _update_layout(fig, df, stock_name):
    """更新图表布局"""
    # 更新图表布局，添加周期切换按钮
    fig.update_layout(
        height=800, width=1080, 
        title={
            'text': f'<b>TrendSight<b> · {stock_name}',
            'font': dict(family="SartSans-Regular", size=40, color="#222222")
        }, 
        title_x=0.475, 
        legend_title='图例',
        xaxis_rangeslider_visible=False,
        margin=dict(l=50, r=50, t=200, b=50),
        updatemenus=[
            dict(
                type="buttons",
                direction="left",
                buttons=list([
                    dict(
                        args=[{"xaxis.range": [df['日期'].iloc[0], df['日期'].iloc[-1]]}],
                        label="1年",
                        method="relayout"
                    ),
                    dict(
                        args=[{"xaxis.range": [df['日期'].iloc[-126], df['日期'].iloc[-1]]}] if len(df) >= 126 else [{"xaxis.range": [df['日期'].iloc[0], df['日期'].iloc[-1]]}],
                        label="半年",
                        method="relayout"
                    ),
                    dict(
                        args=[{"xaxis.range": [df['日期'].iloc[-63], df['日期'].iloc[-1]]}] if len(df) >= 63 else [{"xaxis.range": [df['日期'].iloc[0], df['日期'].iloc[-1]]}],
                        label="1季度",
                        method="relayout"
                    ),
                    dict(
                        args=[{"xaxis.range": [df['日期'].iloc[-21], df['日期'].iloc[-1]]}] if len(df) >= 21 else [{"xaxis.range": [df['日期'].iloc[0], df['日期'].iloc[-1]]}],
                        label="1月",
                        method="relayout"
                    ),
                ]),
                pad={"r": 10, "t": 10, "b": 10, "l": 10},
                showactive=True,
                x=0.5,
                xanchor="center",
                y=1.05,
                yanchor="bottom",
                bgcolor="rgba(255, 255, 255, 0.95)",
                bordercolor="#CCC",
                borderwidth=1,
                font=dict(size=12, color="#333")
            ),
        ]
    )

    # 更新y轴的标题
    fig.update_yaxes(title_text='价格', type="log", row=1, col=1)
    fig.update_yaxes(title_text='交易量', row=2, col=1)
    fig.update_yaxes(title_text='RSI', row=3, col=1, range=[0, 100])

    # x轴格式化和网格线设置
    fig.update_xaxes(showgrid=False)
    fig.update_xaxes(
        tickformat="%Y-%m-%d",
        tickangle=45,
        nticks=10,
        row=3, col=1  # 只在最底部的子图显示日期标签
    )