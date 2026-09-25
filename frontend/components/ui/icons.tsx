import type { ComponentType } from "react";
import type { IconBaseProps } from "@ant-design/icons/lib/components/Icon";

import { PlusOutlined, ArrowRightOutlined, CheckOutlined, LeftOutlined, RightOutlined, CloseOutlined, DeleteOutlined, EditOutlined, DoubleLeftOutlined, DoubleRightOutlined, LinkOutlined, SearchOutlined, WarningOutlined } from "@ant-design/icons";

export type IconProps = IconBaseProps & { size?: number; color?: string };
function adapt(Icon: ComponentType<IconBaseProps>) { return function AdaptedIcon({ size, color, style, ...props }: IconProps) { return <Icon style={{ fontSize: size, color, ...style }} {...props} />; }; }
export const AlertTriangle = adapt(WarningOutlined);
export const ArrowRight = adapt(ArrowRightOutlined);
export const Check = adapt(CheckOutlined);
export const ChevronLeft = adapt(LeftOutlined);
export const ChevronRight = adapt(RightOutlined);
export const ChevronsLeft = adapt(DoubleLeftOutlined);
export const ChevronsRight = adapt(DoubleRightOutlined);
export const Pencil = adapt(EditOutlined);
export const Plus = adapt(PlusOutlined);
export const Search = adapt(SearchOutlined);
export const Trash2 = adapt(DeleteOutlined);
export const X = adapt(CloseOutlined);
export const ExternalLink = adapt(LinkOutlined);
