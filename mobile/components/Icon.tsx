import { Platform } from 'react-native';
import Svg, { Path } from 'react-native-svg';

// The few icons the app uses, inlined as SVG paths instead of loading a 1.3 MB icon font.
// Paths from Material Design Icons (Pictogrammers, @mdi/js 7.4.47), Apache License 2.0.
const PATHS = {
  'alert-octagon':
    'M13 13H11V7H13M11 15H13V17H11M15.73 3H8.27L3 8.27V15.73L8.27 21H15.73L21 15.73V8.27L15.73 3Z',
  alert: 'M13 14H11V9H13M13 18H11V16H13M1 21H23L12 2L1 21Z',
  'check-circle-outline':
    'M12 2C6.5 2 2 6.5 2 12S6.5 22 12 22 22 17.5 22 12 17.5 2 12 2M12 20C7.59 20 4 16.41 4 12S7.59 4 12 4 20 7.59 20 12 16.41 20 12 20M16.59 7.58L10 14.17L7.41 11.59L6 13L10 17L18 9L16.59 7.58Z',
  'lock-outline':
    'M12,17C10.89,17 10,16.1 10,15C10,13.89 10.89,13 12,13A2,2 0 0,1 14,15A2,2 0 0,1 12,17M18,20V10H6V20H18M18,8A2,2 0 0,1 20,10V20A2,2 0 0,1 18,22H6C4.89,22 4,21.1 4,20V10C4,8.89 4.89,8 6,8H7V6A5,5 0 0,1 12,1A5,5 0 0,1 17,6V8H18M12,3A3,3 0 0,0 9,6V8H15V6A3,3 0 0,0 12,3Z',
} as const;

export type IconName = keyof typeof PATHS;

type Props = {
  name: IconName;
  size: number;
  color: string;
  testID?: string;
};

// Decorative icons are always paired with text, so they are hidden from screen readers.
// On web the SVG is a DOM element and takes aria-hidden; the native-only props would end
// up as unknown DOM attributes there.
const HIDDEN_FROM_ACCESSIBILITY =
  Platform.OS === 'web'
    ? ({ 'aria-hidden': true } as const)
    : ({
        accessibilityElementsHidden: true,
        importantForAccessibility: 'no-hide-descendants',
      } as const);

export function Icon({ name, size, color, testID }: Props) {
  return (
    <Svg
      testID={testID}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      {...HIDDEN_FROM_ACCESSIBILITY}
    >
      <Path d={PATHS[name]} fill={color} />
    </Svg>
  );
}
