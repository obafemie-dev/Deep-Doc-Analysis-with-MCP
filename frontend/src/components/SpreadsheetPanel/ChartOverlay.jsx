/**
 * ChartOverlay - Renders a chart overlay on top of the spreadsheet grid
 */
import React, { useMemo } from 'react';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  AreaChart,
  Area,
  ComposedChart,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  Cell,
  ResponsiveContainer
} from 'recharts';

// Color palette for charts
const COLORS = [
  '#3B82F6', // blue
  '#10B981', // green
  '#F59E0B', // amber
  '#EF4444', // red
  '#8B5CF6', // purple
  '#EC4899', // pink
  '#06B6D4', // cyan
  '#F97316', // orange
];

/**
 * Transform backend chart data to Recharts format
 */
function transformDataForRecharts(chartData) {
  const { labels, datasets } = chartData;

  if (!labels || !datasets || datasets.length === 0) {
    return [];
  }

  // Create data array with labels and all dataset values
  return labels.map((label, index) => {
    const point = { name: label };
    datasets.forEach((dataset, dsIndex) => {
      const key = dataset.label || `series_${dsIndex}`;
      point[key] = dataset.data[index] ?? 0;
    });
    return point;
  });
}

/**
 * Transform data for pie charts
 */
function transformDataForPie(chartData) {
  const { labels, datasets } = chartData;

  if (!labels || !datasets || datasets.length === 0) {
    return [];
  }

  // Use first dataset for pie chart
  const dataset = datasets[0];
  return labels.map((label, index) => ({
    name: label,
    value: dataset.data[index] ?? 0
  }));
}

function ChartOverlay({
  chart,
  viewport,
  cellWidth,
  cellHeight,
  rowHeaderWidth,
  colHeaderHeight
}) {
  const { id, type, anchor, size, title, data } = chart;

  // Calculate position relative to viewport
  const relativeRow = anchor.row - viewport.start_row;
  const relativeCol = anchor.col - viewport.start_col;

  // Skip if chart anchor is outside viewport
  if (relativeRow < 0 || relativeCol < 0) {
    return null;
  }

  // Calculate pixel position
  const left = rowHeaderWidth + (relativeCol * cellWidth);
  const top = colHeaderHeight + (relativeRow * cellHeight);

  // Transform data for Recharts
  const rechartsData = useMemo(() => {
    if (type === 'pie') {
      return transformDataForPie(data);
    }
    return transformDataForRecharts(data);
  }, [data, type]);

  // Get dataset keys for rendering
  const datasetKeys = useMemo(() => {
    if (!data.datasets) return [];
    return data.datasets.map((ds, idx) => ds.label || `series_${idx}`);
  }, [data.datasets]);

  // Render appropriate chart type
  const renderChart = () => {
    const commonProps = {
      data: rechartsData,
      margin: { top: 20, right: 20, bottom: 20, left: 20 }
    };

    switch (type) {
      case 'bar':
        return (
          <BarChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 10 }}
              stroke="#6B7280"
            />
            <YAxis tick={{ fontSize: 10 }} stroke="#6B7280" />
            <Tooltip
              contentStyle={{
                backgroundColor: 'white',
                border: '1px solid #E5E7EB',
                borderRadius: '6px',
                fontSize: '12px'
              }}
            />
            <Legend wrapperStyle={{ fontSize: '10px' }} />
            {datasetKeys.map((key, index) => (
              <Bar
                key={key}
                dataKey={key}
                fill={COLORS[index % COLORS.length]}
              />
            ))}
          </BarChart>
        );

      case 'line':
        return (
          <LineChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 10 }}
              stroke="#6B7280"
            />
            <YAxis tick={{ fontSize: 10 }} stroke="#6B7280" />
            <Tooltip
              contentStyle={{
                backgroundColor: 'white',
                border: '1px solid #E5E7EB',
                borderRadius: '6px',
                fontSize: '12px'
              }}
            />
            <Legend wrapperStyle={{ fontSize: '10px' }} />
            {datasetKeys.map((key, index) => (
              <Line
                key={key}
                type="monotone"
                dataKey={key}
                stroke={COLORS[index % COLORS.length]}
                strokeWidth={2}
                dot={{ r: 3 }}
              />
            ))}
          </LineChart>
        );

      case 'pie':
        return (
          <PieChart>
            <Pie
              data={rechartsData}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              outerRadius={Math.min(size.width, size.height) / 3}
              label={({ name, percent }) =>
                `${name}: ${(percent * 100).toFixed(0)}%`
              }
              labelLine={{ stroke: '#6B7280', strokeWidth: 1 }}
            >
              {rechartsData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={COLORS[index % COLORS.length]}
                />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                backgroundColor: 'white',
                border: '1px solid #E5E7EB',
                borderRadius: '6px',
                fontSize: '12px'
              }}
            />
            <Legend wrapperStyle={{ fontSize: '10px' }} />
          </PieChart>
        );

      case 'area':
        return (
          <AreaChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 10 }}
              stroke="#6B7280"
            />
            <YAxis tick={{ fontSize: 10 }} stroke="#6B7280" />
            <Tooltip
              contentStyle={{
                backgroundColor: 'white',
                border: '1px solid #E5E7EB',
                borderRadius: '6px',
                fontSize: '12px'
              }}
            />
            <Legend wrapperStyle={{ fontSize: '10px' }} />
            {datasetKeys.map((key, index) => (
              <Area
                key={key}
                type="monotone"
                dataKey={key}
                fill={COLORS[index % COLORS.length]}
                fillOpacity={0.3}
                stroke={COLORS[index % COLORS.length]}
                strokeWidth={2}
              />
            ))}
          </AreaChart>
        );

      case 'combo':
        // Composed chart with bars and lines
        return (
          <ComposedChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 10 }}
              stroke="#6B7280"
            />
            <YAxis yAxisId="left" tick={{ fontSize: 10 }} stroke="#6B7280" />
            <YAxis
              yAxisId="right"
              orientation="right"
              tick={{ fontSize: 10 }}
              stroke="#6B7280"
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'white',
                border: '1px solid #E5E7EB',
                borderRadius: '6px',
                fontSize: '12px'
              }}
            />
            <Legend wrapperStyle={{ fontSize: '10px' }} />
            {datasetKeys.map((key, index) => {
              // Alternate between bars and lines
              if (index % 2 === 0) {
                return (
                  <Bar
                    key={key}
                    dataKey={key}
                    fill={COLORS[index % COLORS.length]}
                    yAxisId="left"
                  />
                );
              }
              return (
                <Line
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stroke={COLORS[index % COLORS.length]}
                  strokeWidth={2}
                  yAxisId="right"
                />
              );
            })}
          </ComposedChart>
        );

      default:
        // Default to bar chart
        return (
          <BarChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 10 }}
              stroke="#6B7280"
            />
            <YAxis tick={{ fontSize: 10 }} stroke="#6B7280" />
            <Tooltip
              contentStyle={{
                backgroundColor: 'white',
                border: '1px solid #E5E7EB',
                borderRadius: '6px',
                fontSize: '12px'
              }}
            />
            <Legend wrapperStyle={{ fontSize: '10px' }} />
            {datasetKeys.map((key, index) => (
              <Bar
                key={key}
                dataKey={key}
                fill={COLORS[index % COLORS.length]}
              />
            ))}
          </BarChart>
        );
    }
  };

  return (
    <div
      className="absolute bg-white border border-gray-200 rounded-lg shadow-lg overflow-hidden"
      style={{
        left: `${left}px`,
        top: `${top}px`,
        width: `${size.width}px`,
        height: `${size.height}px`,
        zIndex: 5
      }}
    >
      {/* Chart title */}
      {title && (
        <div className="px-3 py-1.5 border-b border-gray-100 bg-gray-50">
          <h4 className="text-xs font-medium text-gray-700 truncate">
            {title}
          </h4>
        </div>
      )}

      {/* Chart content */}
      <div
        className="w-full"
        style={{ height: title ? `calc(100% - 28px)` : '100%' }}
      >
        {rechartsData.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            {renderChart()}
          </ResponsiveContainer>
        ) : (
          <div className="h-full flex items-center justify-center text-gray-400 text-xs">
            No data available
          </div>
        )}
      </div>
    </div>
  );
}

export default ChartOverlay;
