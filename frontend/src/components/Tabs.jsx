export default function Tabs({ tabs, active, onChange }) {
  return (
    <div
      role="tablist"
      className="flex gap-1 border-b border-gray-200 overflow-x-auto"
    >
      {tabs.map((tab) => {
        const selected = tab.id === active;
        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={selected}
            tabIndex={selected ? 0 : -1}
            onClick={() => onChange(tab.id)}
            className={`px-4 py-2.5 text-base font-medium whitespace-nowrap border-b-2 -mb-px ${
              selected
                ? "border-blue-700 text-blue-700"
                : "border-transparent text-gray-700 hover:text-blue-700"
            }`}
          >
            {tab.label}
            {typeof tab.count === "number" && (
              <span
                className={`ml-2 inline-flex items-center justify-center text-xs px-1.5 min-w-5 rounded-full ${
                  selected
                    ? "bg-blue-700 text-white"
                    : "bg-gray-200 text-gray-800"
                }`}
              >
                {tab.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
