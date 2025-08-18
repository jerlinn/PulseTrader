import plotly.graph_objs as go
from plotly.subplots import make_subplots
from decimal import Decimal
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

    # 添加增强的成交量可视化
    _add_enhanced_volume_bars(fig, trading_df, df)

    # 添加超级趋势上轨线和下轨线
    fig.add_trace(go.Scatter(x=df['日期'], y=df['upper_band'], mode='lines', name='下行', line=dict(color='green', shape='spline', dash='dot')), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['日期'], y=df['lower_band'], mode='lines', name='上行', line=dict(color='orangered', shape='spline', dash='dot')), row=1, col=1)

    _add_ma10_line(fig, df)
    _add_trend_filling(fig, df)
    _add_signal_markers(fig, df)

    # 添加 RSI 指标线到第三个子图
    rsi_col = 'rsi14' if 'rsi14' in df.columns else 'rsi'
    fig.add_trace(go.Scatter(
        x=df['日期'], y=df[rsi_col],
        mode='lines',
        line=dict(color='#FF8C1E', width=2),
        name='RSI'
    ), row=3, col=1)

    # RSI 关键区域参考线-严格
    fig.add_hline(y=80, line_dash="dot", line_color="red", opacity=0.3, row=3, col=1)     # 超买线
    fig.add_hline(y=20, line_dash="dot", line_color="green", opacity=0.3, row=3, col=1)   # 超卖线

    # 添加 RSI 背离标记
    if not divergences.empty:
        _add_divergence_markers(fig, df, divergences)
        
    _update_layout(fig, df, stock_name)

    fig_name = f'{output_directory}/{stock_name}_PulseTrader_{today}.png'
    html_name = f'{output_directory}/{stock_name}_PulseTrader_{today}.html'
    
    fig.write_image(fig_name, scale=2)
    fig.write_html(html_name)
    
    print(f"图表已保存至: {fig_name}")
    print(f"HTML 版本已保存至: {html_name}")
    return fig

def _add_ma10_line(fig, df):
    """添加 MA10"""
    # 检查是否有已计算的 ma10 列，如果没有则计算
    if 'ma10' in df.columns:
        ma_10 = df['ma10']
    else:
        # 作为后备，如果数据库中没有 ma10，则临时计算
        ma_10 = df['收盘'].rolling(window=10).mean()

    # 确保 trend 列存在
    if 'trend' not in df.columns:
        print("⚠️  MA10绘制: 缺少 trend 列，使用默认中性颜色")
        df['trend'] = 0  # 添加默认 trend 列
    
    fig.add_trace(go.Scatter(
        x=df['日期'], 
        y=ma_10,
        mode='lines', 
        line=dict(color='#0CAEE6', width=1, shape='spline'),
        name='MA10',
        showlegend=True
    ), row=1, col=1)

def _add_trend_filling(fig, df):
    """添加趋势填充区域"""
    # 确保 trend 列存在
    if 'trend' not in df.columns:
        print("⚠️  趋势填充: 缺少 trend 列，跳过填充")
        return
        
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
    # 确保 trend 列存在
    if 'trend' not in df.columns:
        print("⚠️  信号标记: 缺少 trend 列，跳过信号标记")
        return
        
    # 计算趋势变化点
    df['trend_shifted'] = df['trend'].shift(1)
    b_positions = df[(df['trend'] == 1) & (df['trend_shifted'] != 1)].index
    s_positions = df[(df['trend'] == -1) & (df['trend_shifted'] != -1)].index
    
    # 在 B 信号的位置上添加标记，使用下轨值（lower_band）作为位置
    fig.add_trace(go.Scatter(
        x=[df.loc[pos, '日期'] for pos in b_positions], 
        y=[df.loc[pos, 'lower_band'] * Decimal('0.994') for pos in b_positions],
        mode='markers', name='UP', 
        marker=dict(symbol='arrow', color='orangered', size=10)
    ), row=1, col=1)

    # 在 S 信号的位置上添加标记，使用上轨值（upper_band）作为位置
    fig.add_trace(go.Scatter(
        x=[df.loc[pos, '日期'] for pos in s_positions], 
        y=[df.loc[pos, 'upper_band'] * Decimal('1.006') for pos in s_positions],
        mode='markers', name='DOWN', 
        marker=dict(symbol='arrow', angle=180, color='green', size=10)
    ), row=1, col=1)

def _add_divergence_markers(fig, df, divergences):
    """添加 RSI 背离标记"""
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
                line_color="rgba(255, 255, 255, 0.9)",
                line_width=1,
                row=1, col=1
            )
            
            # 在 RSI 图上标记背离
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

def _add_enhanced_volume_bars(fig, trading_df, df):
    """添加增强的成交量可视化，突出显示极致缩量、放量、爆量"""
    
    # 检查必要的成交量指标列是否存在
    volume_indicator_cols = ['is_low_vol_bar', 'is_high_vol_bar', 'is_sky_vol_bar']
    has_volume_indicators = all(col in df.columns for col in volume_indicator_cols)
    
    if not has_volume_indicators:
        _add_basic_volume_bars(fig, trading_df)
        return
    
    # 不需要 merge，因为 trading_df 本身就是从 df 筛得出
    enhanced_trading_df = df[df['日期'].notnull()].copy()
    
    # 计算涨跌幅用于颜色
    enhanced_trading_df['Change'] = enhanced_trading_df['收盘'] - enhanced_trading_df['开盘']
    
    # 为不同类型的成交量柱设置不同颜色
    volume_colors = []
    for _, row in enhanced_trading_df.iterrows():
        if row['is_low_vol_bar']:
            volume_colors.append('#77BF4D')  # 极致缩量：绿色
        elif row['Change'] > 0:
            volume_colors.append('red')  # 所有上涨（包括普通涨、高量、天量）：红色
        else:
            volume_colors.append('green')  # 下跌：绿色
    
    # 创建自定义的hover信息，包含成交量类型
    hover_texts = []
    for _, row in enhanced_trading_df.iterrows():
        vol_type = ""
        if row['is_sky_vol_bar']:
            vol_type = " (爆量)"
        elif row['is_high_vol_bar']:
            vol_type = " (放量)"
        elif row['is_low_vol_bar']:
            vol_type = " (极致缩量)"
        
        hover_texts.append(f"日期: {row['日期'].strftime('%Y-%m-%d')}<br>成交量: {row['成交量']:,.0f}{vol_type}")
    
    # 添加主要的成交量柱状图（带颜色区分和类型说明）
    fig.add_trace(go.Bar(
        x=enhanced_trading_df['日期'], 
        y=enhanced_trading_df['成交量'], 
        marker_color=volume_colors, 
        name='交易量',
        hovertemplate='%{customdata}<extra></extra>',
        customdata=hover_texts
    ), row=2, col=1)
    
    # 添加顶部标记来区分天量柱和高量柱
    _add_volume_top_markers(fig, enhanced_trading_df)

def _add_basic_volume_bars(fig, trading_df):
    """添加基础成交量柱状图（当成交量指标不可用时的回退方案）"""
    # 计算涨跌幅用于颜色
    trading_df = trading_df.copy()
    trading_df['Change'] = trading_df['收盘'] - trading_df['开盘']
    trading_df['Color'] = trading_df['Change'].apply(lambda x: 'red' if x > 0 else 'green')

    # 基础交易量柱状图
    fig.add_trace(go.Bar(
        x=trading_df['日期'], 
        y=trading_df['成交量'], 
        marker_color=trading_df['Color'], 
        name='交易量',
        hovertemplate='日期: %{x}<br>成交量: %{y:,.0f}<extra></extra>'
    ), row=2, col=1)

def _add_volume_top_markers(fig, df):
    """在红色成交量柱顶部添加标记来区分爆量和放量"""
    
    if '成交量' not in df.columns or df.empty:
        return
    
    try:
        # 爆量标记：实心圆 ●
        sky_vol_data = df[df['is_sky_vol_bar'] == True]
        if not sky_vol_data.empty:
            # 在成交量图上添加标记
            fig.add_trace(go.Scatter(
                x=sky_vol_data['日期'],
                y=sky_vol_data['成交量'] * 1.1,
                mode='markers',
                marker=dict(size=4, color='red', symbol='circle'),
                name='爆量',
                showlegend=False,
                hovertemplate='爆量<br>日期: %{x}<br>成交量: %{y:,.0f}<extra></extra>'
            ), row=2, col=1)
            
            # 为每个爆量在第一个价格子图添加垂直辅助线
            for date in sky_vol_data['日期']:
                fig.add_vline(
                    x=date,
                    line_dash="solid",
                    line_color="rgba(255, 255, 255, 0.9)",
                    line_width=1,
                    row=1, col=1
                )
        
        # 放量标记：空心圆 ○
        high_vol_data = df[df['is_high_vol_bar'] == True]
        if not high_vol_data.empty:
            fig.add_trace(go.Scatter(
                x=high_vol_data['日期'],
                y=high_vol_data['成交量'] * 1.1,
                mode='markers',
                marker=dict(size=4, color='red', symbol='circle-open', line=dict(width=1)),
                name='放量',
                showlegend=False,
                hovertemplate='放量<br>日期: %{x}<br>成交量: %{y:,.0f}<extra></extra>'
            ), row=2, col=1)
    except Exception:
        # 静默跳过标记添加失败
        pass

def _update_layout(fig, df, stock_name):
    """更新图表布局，添加周期切换按钮"""
    fig.update_layout(
        height=800, width=1080, 
        title={
            'text': f'<b>PulseTrader<b> · {stock_name}',
            'font': dict(family="Smiley Sans", size=40, color="#222222") #自用 SartSans-Regular
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

    fig.update_yaxes(title_text='价格', type="log", row=1, col=1)
    fig.update_yaxes(title_text='交易量', row=2, col=1)
    fig.update_yaxes(title_text='RSI', row=3, col=1, range=[0, 100])

    fig.update_xaxes(showgrid=False)
    fig.update_xaxes(
        tickformat="%Y-%m-%d",
        tickangle=45,
        nticks=10,
        row=3, col=1  # 只在最底部的子图显示日期标签
    )