import type { HTMLAttributes, TableHTMLAttributes, ThHTMLAttributes, TdHTMLAttributes } from "react";

type WithId = { id: string };
type TableProps = TableHTMLAttributes<HTMLTableElement> & WithId;
type SectionProps = HTMLAttributes<HTMLTableSectionElement> & WithId;
type RowProps = HTMLAttributes<HTMLTableRowElement> & WithId;
type HeadProps = ThHTMLAttributes<HTMLTableCellElement> & WithId;
type CellProps = TdHTMLAttributes<HTMLTableCellElement> & WithId;

export function Table({ id, ...props }: TableProps) { return <table id={id} {...props} />; }
export function TableHeader({ id, ...props }: SectionProps) { return <thead id={id} {...props} />; }
export function TableBody({ id, ...props }: SectionProps) { return <tbody id={id} {...props} />; }
export function TableRow({ id, ...props }: RowProps) { return <tr id={id} {...props} />; }
export function TableHead({ id, ...props }: HeadProps) { return <th id={id} scope="col" {...props} />; }
export function TableCell({ id, ...props }: CellProps) { return <td id={id} {...props} />; }
