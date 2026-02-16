export interface ApplicationData {
  brandName: string;
  classType: string;
  alcoholContent: string;
  netContents: string;
  producerName: string;
  countryOfOrigin: string;
  governmentWarning: string;
}

export interface FieldResult {
  field: string;
  extracted: string;
  expected: string;
  status: 'pass' | 'fail' | 'warning';
  note?: string;
}

export interface VerificationResult {
  overallStatus: 'approved' | 'rejected' | 'review';
  fields: FieldResult[];
  summary: string;
}