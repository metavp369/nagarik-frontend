// Nagarik — Civic Issue Categories
export const CIVIC_CATEGORIES = [
  {
    id: 'roads',
    label: 'Roads & Potholes',
    labelHindi: '???? ?? ?????',
    dept: 'PWD',
    icon: '???',
    sla_hours: 72,
    escalation: {
      L1: { role: 'Ward Officer',         notify: 'ward.officer@{city}.gov.in' },
      L2: { role: 'Circle Officer',       notify: 'circle.officer@{city}.gov.in' },
      L3: { role: 'Commissioner',         notify: 'commissioner@{city}.gov.in' },
    },
    keywords: ['pothole','road','crater','broken road','uneven','sinkhole'],
  },
  {
    id: 'water',
    label: 'Water Supply',
    labelHindi: '???? ?? ??????',
    dept: 'Jal Board',
    icon: '??',
    sla_hours: 24,
    escalation: {
      L1: { role: 'Jal Board AE',         notify: 'ae@jalboard.{city}.gov.in' },
      L2: { role: 'Jal Board EE',         notify: 'ee@jalboard.{city}.gov.in' },
      L3: { role: 'MD Jal Board',         notify: 'md@jalboard.{city}.gov.in' },
    },
    keywords: ['water','pipe','leak','no water','dirty water','flooding'],
  },
  {
    id: 'garbage',
    label: 'Garbage Collection',
    labelHindi: '???? ??????',
    dept: 'Municipal Corporation',
    icon: '???',
    sla_hours: 48,
    escalation: {
      L1: { role: 'Sanitation Inspector', notify: 'sanitation@{city}.gov.in' },
      L2: { role: 'Zonal Officer',        notify: 'zonal@{city}.gov.in' },
      L3: { role: 'Commissioner',         notify: 'commissioner@{city}.gov.in' },
    },
    keywords: ['garbage','waste','trash','dumping','smell','littering'],
  },
  {
    id: 'electricity',
    label: 'Street Lights / Power',
    labelHindi: '????? ??????',
    dept: 'DISCOM',
    icon: '??',
    sla_hours: 12,
    escalation: {
      L1: { role: 'DISCOM JE',            notify: 'je@discom.{city}.gov.in' },
      L2: { role: 'DISCOM AE',            notify: 'ae@discom.{city}.gov.in' },
      L3: { role: 'Superintending Engg',  notify: 'se@discom.{city}.gov.in' },
    },
    keywords: ['light','electricity','power','dark','streetlight','outage'],
  },
  {
    id: 'sewage',
    label: 'Drainage & Sewage',
    labelHindi: '???? ?? ????',
    dept: 'Municipal Corporation',
    icon: '??',
    sla_hours: 48,
    escalation: {
      L1: { role: 'Sanitation Inspector', notify: 'sanitation@{city}.gov.in' },
      L2: { role: 'Zonal Officer',        notify: 'zonal@{city}.gov.in' },
      L3: { role: 'Commissioner',         notify: 'commissioner@{city}.gov.in' },
    },
    keywords: ['drain','sewage','overflow','blocked','sewer','stink'],
  },
  {
    id: 'encroachment',
    label: 'Encroachment',
    labelHindi: '????????',
    dept: 'Revenue Department',
    icon: '???',
    sla_hours: 96,
    escalation: {
      L1: { role: 'Revenue Inspector',    notify: 'ri@revenue.{city}.gov.in' },
      L2: { role: 'Tehsildar',            notify: 'tehsildar@revenue.{city}.gov.in' },
      L3: { role: 'SDM',                  notify: 'sdm@revenue.{city}.gov.in' },
    },
    keywords: ['encroachment','illegal','obstruction','blocked path'],
  },
  {
    id: 'parks',
    label: 'Parks & Public Spaces',
    labelHindi: '????? ?? ????????? ?????',
    dept: 'Parks Department',
    icon: '??',
    sla_hours: 72,
    escalation: {
      L1: { role: 'Parks Inspector',      notify: 'parks@{city}.gov.in' },
      L2: { role: 'Zonal Officer',        notify: 'zonal@{city}.gov.in' },
      L3: { role: 'Commissioner',         notify: 'commissioner@{city}.gov.in' },
    },
    keywords: ['park','garden','bench','broken','dirty','unsafe'],
  },
];

export const getCategoryById = (id) => CIVIC_CATEGORIES.find((c) => c.id === id);
export const getCategoryByKeyword = (text) => {
  const lower = text.toLowerCase();
  return CIVIC_CATEGORIES.find((c) => c.keywords.some((kw) => lower.includes(kw)));
};
