import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

// Placeholder data — swap for API response (GET /api/movement?range=week).
const data = [
  { day: "M", movements: 42 },
  { day: "T", movements: 68 },
  { day: "W", movements: 55 },
  { day: "T ", movements: 90 },
  { day: "F", movements: 74 },
  { day: "S", movements: 48 },
  { day: "S ", movements: 61 },
];

export function MovementChart() {
  return (
    <div className="h-44 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={data}
          margin={{ top: 8, right: 8, left: -24, bottom: 0 }}
        >
          <defs>
            <linearGradient id="movementFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#E1E0CC" stopOpacity={0.35} />
              <stop offset="100%" stopColor="#E1E0CC" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid
            stroke="rgba(255,255,255,0.05)"
            vertical={false}
          />
          <XAxis
            dataKey="day"
            tick={{
              fill: "rgba(225,224,204,0.6)",
              fontSize: 10,
              letterSpacing: "0.15em",
            }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            tick={{
              fill: "rgba(225,224,204,0.4)",
              fontSize: 10,
            }}
            tickLine={false}
            axisLine={false}
            width={32}
          />
          <Tooltip
            cursor={{ stroke: "rgba(225,224,204,0.15)", strokeWidth: 1 }}
            contentStyle={{
              background: "#101010",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: 8,
              fontSize: 12,
              color: "#E1E0CC",
            }}
            labelStyle={{ color: "rgba(225,224,204,0.6)" }}
          />
          <Area
            type="monotone"
            dataKey="movements"
            stroke="#E1E0CC"
            strokeWidth={1.5}
            fill="url(#movementFill)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}