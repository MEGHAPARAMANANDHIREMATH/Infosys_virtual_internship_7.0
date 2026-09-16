import { useState } from 'react';

const TABS = [
  { id: 'scope', label: 'Scope & Deliverables' },
  { id: 'risks', label: 'Risk Analysis' },
  { id: 'forecast', label: 'Delivery Forecast' },
  { id: 'blockers', label: 'Blockers' },
  { id: 'decisions', label: 'Pending Decisions' },
  { id: 'actions', label: 'Action Items' },
];

const SEVERITY_STYLES = {
  Low: 'bg-slate-100 text-slate-700',
  Medium: 'bg-amber-100 text-amber-800',
  High: 'bg-orange-100 text-orange-800',
  Critical: 'bg-red-100 text-red-800',
};

const FORECAST_STYLES = {
  'ON TRACK': 'bg-emerald-100 text-emerald-800',
  'AT RISK': 'bg-amber-100 text-amber-800',
  DELAYED: 'bg-red-100 text-red-800',
};

export default function AgentResultsDashboard({ result, sourceName, loading }) {
  const [tab, setTab] = useState('scope');

  if (loading && !result) {
    return (
      <div className="border border-dashed border-slate-300 rounded-xl p-8 text-center text-sm text-slate-500">
        Processing document...
      </div>
    );
  }

  if (!result) {
    return (
      <div className="border border-dashed border-slate-300 rounded-xl p-8 text-center text-sm text-slate-500">
        Run an agent to see structured results for the selected document.
      </div>
    );
  }

  const scope = result.scope;
  const risks = result.risks || [];
  const forecast = result.forecast;
  const blockers = result.blockers || {};

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-600">
        Source document: <span className="font-medium text-slate-900">{sourceName || result.file_name}</span>
      </p>
      <div className="flex flex-wrap gap-2">
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setTab(item.id)}
            className={`px-3 py-1.5 rounded-lg text-xs sm:text-sm ${
              tab === item.id ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-700'
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>

      {tab === 'scope' && <ScopePanel scope={scope} />}
      {tab === 'risks' && (
        <TablePanel
          empty="No risks were identified in this document."
          columns={['Risk', 'Category', 'Severity', 'Evidence', 'Affected Task/Milestone', 'Mitigation']}
          rows={(risks || []).map((row) => [
            row.risk,
            row.category,
            <Severity key="s" value={row.severity} />,
            row.evidence,
            row.affected,
            row.mitigation,
          ])}
        />
      )}
      {tab === 'forecast' && <ForecastPanel forecast={forecast} />}
      {tab === 'blockers' && (
        <div className="space-y-6">
          <TablePanel
            title="Blockers"
            empty="No blockers were found in this document."
            columns={['Blocker', 'Evidence', 'Owner', 'Priority', 'Status']}
            rows={(blockers.blockers || []).map((row) => [
              row.blocker,
              row.evidence,
              row.owner,
              row.priority,
              row.status,
            ])}
          />
          <TablePanel
            title="Open Issues"
            empty="No open issues were found in this document."
            columns={['Issue', 'Evidence', 'Owner', 'Priority', 'Status']}
            rows={(blockers.open_issues || []).map((row) => [
              row.issue,
              row.evidence,
              row.owner,
              row.priority,
              row.status,
            ])}
          />
        </div>
      )}
      {tab === 'decisions' && (
        <TablePanel
          empty="No pending decisions were found in this document."
          columns={['Decision Required', 'Evidence', 'Responsible Person', 'Due Date', 'Status']}
          rows={(blockers.pending_decisions || []).map((row) => [
            row.decision,
            row.evidence,
            row.responsible_person,
            row.due_date,
            row.status,
          ])}
        />
      )}
      {tab === 'actions' && (
        <TablePanel
          empty="No action items were found in this document."
          columns={['Action Item', 'Owner', 'Due Date', 'Priority', 'Status']}
          rows={(blockers.action_items || []).map((row) => [
            row.action_item,
            row.owner,
            row.due_date,
            row.priority,
            row.status,
          ])}
        />
      )}
    </div>
  );
}

function ScopePanel({ scope }) {
  if (!scope) {
    return <Empty text="Scope results are not available. Run the Scope & Deliverables agent." />;
  }
  return (
    <div className="space-y-6">
      <section>
        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Project Overview</h3>
        <dl className="mt-3 grid gap-3 sm:grid-cols-2">
          <Item label="Project Name" value={scope.project_name} />
          <Item label="Start date" value={scope.start_date} />
          <Item label="Deadline / end date" value={scope.end_date} />
          <Item label="Objective" value={scope.objective} wide />
          <Item label="Scope" value={scope.scope} wide />
        </dl>
      </section>
      <TablePanel
        title="Deliverables"
        empty="No deliverables were specified."
        columns={['Deliverable', 'Owner', 'Deadline', 'Status']}
        rows={(scope.deliverables || []).map((row) => [row.deliverable, row.owner, row.deadline, row.status])}
      />
      <TablePanel
        title="Milestones"
        empty="No milestones were specified."
        columns={['Milestone', 'Date', 'Owner', 'Status']}
        rows={(scope.milestones || []).map((row) => [row.milestone, row.date, row.owner, row.status])}
      />
      <TablePanel
        title="Tasks"
        empty="No tasks were specified."
        columns={['Task', 'Owner', 'Deadline', 'Status', 'Depends on']}
        rows={(scope.tasks || []).map((row) => [row.task, row.owner, row.deadline, row.status, row.depends_on])}
      />
      <TablePanel
        title="Dependencies"
        empty="No dependencies were specified."
        columns={['Dependency', 'Related Task', 'Status']}
        rows={(scope.dependencies || []).map((row) => [row.dependency, row.related_task, row.status])}
      />
      <TablePanel
        title="Responsibilities"
        empty="No owners were specified."
        columns={['Name', 'Role']}
        rows={(scope.responsibilities || []).map((row) => [row.name, row.role])}
      />
    </div>
  );
}

function ForecastPanel({ forecast }) {
  if (!forecast) {
    return <Empty text="Delivery forecast is not available. Run the Risk & Delivery Forecast agent." />;
  }
  return (
    <div className="space-y-4">
      <div>
        <p className="text-xs uppercase tracking-wide text-slate-500">Status</p>
        <span
          className={`inline-block mt-2 px-3 py-1 rounded-lg text-sm font-semibold ${
            FORECAST_STYLES[forecast.status] || 'bg-slate-100'
          }`}
        >
          {forecast.status}
        </span>
      </div>
      <Item label="Reason" value={forecast.reason} wide />
      <List label="Key Risks" values={forecast.key_risks} />
      <List label="Affected Milestones" values={forecast.affected_milestones} />
      <List label="Recommended Actions" values={forecast.recommended_actions} />
    </div>
  );
}

function TablePanel({ title, columns, rows, empty }) {
  return (
    <section>
      {title && <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500 mb-3">{title}</h3>}
      {!rows || rows.length === 0 ? (
        <Empty text={empty} />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-[40rem]">
            <thead>
              <tr className="text-left text-slate-500 border-b">
                {columns.map((column) => (
                  <th key={column} className="py-2 pr-3 font-medium">
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={index} className="border-b border-slate-100 align-top">
                  {row.map((cell, cellIndex) => (
                    <td key={cellIndex} className="py-2 pr-3 text-slate-800">
                      {cell || 'Not specified'}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function Item({ label, value, wide }) {
  return (
    <div className={wide ? 'sm:col-span-2' : ''}>
      <dt className="text-xs uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="text-sm text-slate-800 mt-1">{value || 'Not specified'}</dd>
    </div>
  );
}

function List({ label, values }) {
  const items = values || [];
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      {items.length === 0 ? (
        <p className="text-sm text-slate-500 mt-1">Not specified</p>
      ) : (
        <ul className="mt-1 list-disc pl-5 text-sm text-slate-800 space-y-1">
          {items.map((item, index) => (
            <li key={index}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Empty({ text }) {
  return <p className="text-sm text-slate-500">{text}</p>;
}

function Severity({ value }) {
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${SEVERITY_STYLES[value] || 'bg-slate-100'}`}>
      {value || 'Not specified'}
    </span>
  );
}
