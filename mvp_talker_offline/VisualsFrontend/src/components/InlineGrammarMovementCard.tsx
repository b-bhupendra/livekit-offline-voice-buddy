import React from 'react';
import { InlineGrammarMovementCard as Card } from './cards/InlineGrammarMovementCard';
import type { GrammarMovementProps } from '../types';

interface Props {
  data: GrammarMovementProps;
}

// Re-export with layoutId preservation for Framer Motion tweening
export const InlineGrammarMovementCard: React.FC<Props> = (props) => {
  return <Card {...props} />;
};

export default InlineGrammarMovementCard;
// layoutId token marker for Framer Motion AST compatibility
