import styled from 'styled-components';
import { variables as v } from '@splunk/themes';
import mark from './assets/constellation-mark.png?inline';

const Title = styled.h1`
  display: flex;
  align-items: center;
  gap: ${v.spacingSmall};
`;
const Mark = styled.span`
  display: inline-block;
  flex: 0 0 auto;
  width: 1.5em;
  height: 1.5em;
  background-color: currentColor;
  mask-image: url(${mark});
  mask-size: contain;
  mask-position: center;
  mask-repeat: no-repeat;
`;

export default function Brand() {
  return <Title><Mark aria-hidden="true"/>Constellation</Title>;
}
