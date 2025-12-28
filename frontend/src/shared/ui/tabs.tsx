import * as React from "react"
import * as TabsPrimitive from "@radix-ui/react-tabs"

import { cn } from "@/lib/utils"

const Tabs = TabsPrimitive.Root

type TabsListProps = React.ComponentPropsWithoutRef<typeof TabsPrimitive.List> & {
  variant?: "default" | "underline"
}

const TabsList = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.List>,
  TabsListProps
>(({ className, variant = "default", ...props }, ref) => {
  const baseStyles = {
    default: "inline-flex h-9 items-center justify-center rounded-lg bg-muted p-1 text-muted-foreground",
    underline: "w-full flex items-center border-b border-border-default bg-transparent pb-0",
  }

  return (
    <TabsPrimitive.List
      ref={ref}
      className={cn(
        baseStyles[variant],
        className
      )}
      {...props}
    />
  )
})
TabsList.displayName = TabsPrimitive.List.displayName

type TabsTriggerProps = React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger> & {
  variant?: "default" | "underline"
}

const TabsTrigger = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Trigger>,
  TabsTriggerProps
>(({ className, variant = "default", ...props }, ref) => {
  const baseStyles = {
    default: "inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow",
    underline: "relative flex-1 px-4 py-2.5 text-sm font-normal text-text-secondary hover:text-text-primary transition-colors duration-200 border-r border-r-border-subtle last:border-r-0 disabled:opacity-50 data-[state=active]:text-accent-primary data-[state=active]:font-medium after:absolute after:bottom-0 after:left-0 after:right-0 after:h-[2px] after:bg-transparent after:transition-all after:duration-200 data-[state=active]:after:bg-accent-primary ring-offset-background focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent-primary focus-visible:ring-offset-2",
  }

  return (
    <TabsPrimitive.Trigger
      ref={ref}
      className={cn(
        baseStyles[variant],
        className
      )}
      {...props}
    />
  )
})
TabsTrigger.displayName = TabsPrimitive.Trigger.displayName

const TabsContent = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Content>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Content
    ref={ref}
    className={cn(
      "mt-2 ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
      className
    )}
    {...props}
  />
))
TabsContent.displayName = TabsPrimitive.Content.displayName

export { Tabs, TabsList, TabsTrigger, TabsContent }
