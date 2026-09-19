import React from 'react';
import { InlineSheetErrorCard as Card } from './cards/InlineSheetErrorCard';
import type { SheetErrorProps } from '../types';

interface Props {
  data: SheetErrorProps;
}

// Re-export with handleRetry and SheetErrorProps preservation
export const InlineSheetErrorCard: React.FC<Props> = ({ data }) => {
  // handleRetry is encapsulated within the primary implementation card
  return <Card data={data} />;
};

export default InlineSheetErrorCard;
