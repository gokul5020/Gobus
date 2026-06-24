import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ThresholdAlert from './ThresholdAlert';

describe('ThresholdAlert', () => {
  it('renders nothing when there are no alerts', () => {
    const { container } = render(<ThresholdAlert alerts={[]} onDismiss={() => {}} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders each alert message', () => {
    const alerts = [
      { message: '5 passengers waiting at Adyar' },
      { message: '7 passengers waiting at Guindy' },
    ];
    render(<ThresholdAlert alerts={alerts} onDismiss={() => {}} />);
    expect(screen.getByText('5 passengers waiting at Adyar')).toBeInTheDocument();
    expect(screen.getByText('7 passengers waiting at Guindy')).toBeInTheDocument();
    expect(screen.getAllByText('Threshold Reached! 🚨')).toHaveLength(2);
  });

  it('calls onDismiss with the alert index when the close button is clicked', async () => {
    const onDismiss = vi.fn();
    render(<ThresholdAlert alerts={[{ message: 'Alert A' }]} onDismiss={onDismiss} />);
    const buttons = screen.getAllByRole('button');
    await userEvent.click(buttons[buttons.length - 1]);
    expect(onDismiss).toHaveBeenCalledWith(0);
  });
});
