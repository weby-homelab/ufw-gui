import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

interface StatsChartProps {
  data: { hour: string; count: number }[];
}

function StatsChart({ data }: StatsChartProps) {
  return (
    <section className="glass-card" style={{ marginTop: "-10px" }}>
      <h2>Attack Statistics (Last 24h)</h2>
      <div style={{ height: "150px", marginTop: "15px" }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <XAxis dataKey="hour" stroke="#666" />
            <YAxis stroke="#666" />
            <Tooltip />
            <Line type="monotone" dataKey="count" stroke="#ff4444" strokeWidth={3} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

export default StatsChart;
