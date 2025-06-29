// Export status calculation for use elsewhere
export const getTimeValueStatus = (timeValue?: number): 'safe' | 'risk' | 'critical' | null => {
  if (timeValue === undefined || timeValue === null) return null;
  if (timeValue > 1.0) return 'safe';
  if (timeValue > 0.1) return 'risk';
  return 'critical';
};